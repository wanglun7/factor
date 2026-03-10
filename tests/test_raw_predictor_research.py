from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_raw_predictor_research_4h, validate_raw_predictor_data_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_validate_raw_predictor_data_4h_requires_price_spot_index_and_funding(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = validate_raw_predictor_data_4h(panel, config.ts_universe)
    assert report["status"] == "ok"
    assert "spot_prices_4h" in report["required_inputs"]


def test_raw_predictor_research_4h_writes_expected_artifacts(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = run_raw_predictor_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.raw_predictors,
        output_dir=tmp_path / "raw_predictors_4h",
    )

    assert report["state"] == "complete"
    out_dir = tmp_path / "raw_predictors_4h"
    assert (out_dir / "raw_predictor_catalog.csv").exists()
    assert (out_dir / "raw_predictor_coverage.csv").exists()
    assert (out_dir / "raw_predictor_summary.csv").exists()
    assert (out_dir / "raw_predictor_mapping_4h.csv").exists()
    assert (out_dir / "raw_predictor_evidence.md").exists()

    catalog = pd.read_csv(out_dir / "raw_predictor_catalog.csv")
    assert {"name", "family", "readiness", "source_level"}.issubset(catalog.columns)
    assert "vma_20d" in set(catalog["name"])
    assert "sma_price_crossover_12" in set(catalog["name"])
    assert "ema_price_crossover_72" in set(catalog["name"])
    assert "forecasted_funding_rate" not in set(catalog["name"])
    assert "generic_time_series_momentum" not in set(catalog["name"])

    summary = pd.read_csv(out_dir / "raw_predictor_summary.csv")
    assert {"name", "family", "delay_0_spread", "delay_1_spread", "delay_2_spread"}.issubset(summary.columns)
    assert "funding_rate_level" in set(summary["name"])
    assert "sma_price_crossover_12" in set(summary["name"])
    assert "ema_price_crossover_72" in set(summary["name"])


def test_raw_predictor_crossover_outputs_are_binary(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    panel = make_panel(tmp_path)

    from research.raw_predictors import _build_predictor_frame

    frame = _build_predictor_frame(panel, panel.symbols)
    for column in [
        "sma_price_crossover_12",
        "sma_price_crossover_24",
        "sma_price_crossover_72",
        "ema_price_crossover_12",
        "ema_price_crossover_24",
        "ema_price_crossover_72",
    ]:
        values = set(frame[column].dropna().unique().tolist())
        assert values.issubset({0.0, 1.0})
