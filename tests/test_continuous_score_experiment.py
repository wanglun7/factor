from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_continuous_score_experiment_4h, validate_continuous_score_experiment_data_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_validate_continuous_score_experiment_4h(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = validate_continuous_score_experiment_data_4h(panel, config.ts_universe, config.continuous_score_experiment)
    assert report["status"] == "ok"
    assert "moving_zscore_baseline" in report["methods"]
    assert "funding_rate_level" in report["continuous_predictors"]


def test_continuous_score_experiment_writes_expected_artifacts(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = run_continuous_score_experiment_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.continuous_score_experiment,
        output_dir=tmp_path / "continuous_score_experiment_4h",
    )

    assert report["state"] == "complete"
    out_dir = tmp_path / "continuous_score_experiment_4h"
    assert (out_dir / "continuous_score_experiment_summary.csv").exists()
    assert (out_dir / "continuous_score_method_ranking.csv").exists()
    assert (out_dir / "continuous_score_family_summary.csv").exists()
    assert (out_dir / "continuous_score_gate_diagnosis.csv").exists()
    assert (out_dir / "continuous_score_recommendation.md").exists()

    summary = pd.read_csv(out_dir / "continuous_score_experiment_summary.csv")
    assert {"predictor", "method", "spread_preservation_ratio", "direction_alignment_ok"}.issubset(summary.columns)
    assert set(summary["method"]) == {
        "moving_zscore_baseline",
        "ewm_zscore",
        "ts_percentile_rank",
        "level_preserve_clip_scale",
    }
    assert "funding_rate_level" in set(summary["predictor"])

    ranking = pd.read_csv(out_dir / "continuous_score_method_ranking.csv")
    assert {"predictor", "best_method", "gate_diagnosis"}.issubset(ranking.columns)
    assert "relative_basis" in set(ranking["predictor"])


def test_continuous_score_experiment_rank_method_is_bounded(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    from research.continuous_score_experiment import _apply_method
    from research.raw_predictors import _build_predictor_frame

    frame = _build_predictor_frame(panel, panel.symbols)
    series = frame.loc[frame["symbol"] == "BTC", "funding_rate_level"]
    ranked = _apply_method(series, "ts_percentile_rank", config.continuous_score_experiment).dropna()
    assert not ranked.empty
    assert float(ranked.min()) >= -1.0
    assert float(ranked.max()) <= 1.0
