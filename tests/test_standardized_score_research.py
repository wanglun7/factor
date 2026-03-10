from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_standardized_score_research_4h, validate_standardized_score_data_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_validate_standardized_score_data_4h_requires_expected_inputs(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = validate_standardized_score_data_4h(panel, config.ts_universe, config.standardized_scores)
    assert report["status"] == "ok"
    assert report["z_window"] == config.standardized_scores.z_window
    assert report["clip_quantile"] == config.standardized_scores.clip_quantile


def test_standardized_score_research_4h_writes_expected_artifacts(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = run_standardized_score_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.standardized_scores,
        output_dir=tmp_path / "standardized_scores_4h",
    )

    assert report["state"] == "complete"
    out_dir = tmp_path / "standardized_scores_4h"
    assert (out_dir / "standardized_score_catalog.csv").exists()
    assert (out_dir / "standardized_score_panel.parquet").exists()
    assert (out_dir / "standardized_score_summary.csv").exists()
    assert (out_dir / "standardized_score_delay_decay.csv").exists()
    assert (out_dir / "standardized_score_distribution.csv").exists()
    assert (out_dir / "standardized_score_alignment.csv").exists()
    assert (out_dir / "standardized_score_decision_log.md").exists()

    catalog = pd.read_csv(out_dir / "standardized_score_catalog.csv")
    assert "prev_day_return_score" in set(catalog["name"])
    assert "trb_200d_score" in set(catalog["name"])
    assert "funding_rate_level_score" in set(catalog["name"])
    assert catalog.loc[catalog["name"] == "prev_day_return_score", "score_method"].iloc[0] == "ts_percentile_rank"
    assert catalog.loc[catalog["name"] == "amihud_20w_score", "score_method"].iloc[0] == "ewm_zscore"
    assert catalog.loc[catalog["name"] == "relative_basis_score", "score_method"].iloc[0] == "level_preserve_clip_scale"

    summary = pd.read_csv(out_dir / "standardized_score_summary.csv")
    assert {"name", "delay_0_spread", "spread_preservation_ratio", "retain_for_composite_v1", "pass_tier", "selected_method"}.issubset(summary.columns)
    assert "amihud_20w_score" in set(summary["name"])
    assert float(summary.loc[summary["name"] == "sma_price_crossover_72_score", "delay_0_spread"].iloc[0]) != 0.0
    assert summary.loc[summary["name"] == "trb_200d_score", "pass_tier"].iloc[0] == "strong"


def test_standardized_score_rule_mappings_and_continuous_scores(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    from research.raw_predictors import _build_predictor_frame, _catalog
    from research.standardized_scores import _build_standardized_score_frame

    raw_specs = [spec for spec in _catalog() if spec.readiness == "implementable"]
    predictor_frame = _build_predictor_frame(panel, panel.symbols)
    score_frame = _build_standardized_score_frame(predictor_frame, raw_specs, config.standardized_scores)

    binary_values = set(score_frame["sma_price_crossover_12_score"].dropna().unique().tolist())
    assert binary_values.issubset({-1.0, 1.0})

    ternary_values = set(score_frame["trb_200d_score"].dropna().unique().tolist())
    assert ternary_values.issubset({-1.0, 0.0, 1.0})

    continuous = score_frame["prev_day_return_score"].dropna()
    assert not continuous.empty
    assert continuous.std(ddof=0) > 0.0

    amihud = score_frame["amihud_20w_score"].dropna()
    assert not amihud.empty
    assert amihud.std(ddof=0) > 0.0
