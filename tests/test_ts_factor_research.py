from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_ts_factor_research_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_ts_factor_research_4h_writes_expected_artifacts(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = run_ts_factor_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        research_config=config.ts_research,
        backtest_config=config.ts_backtest,
        output_dir=tmp_path / "ts4h_factor_research",
    )

    assert report["state"] == "complete"
    out_dir = tmp_path / "ts4h_factor_research"
    assert (out_dir / "ts4h_factor_summary.csv").exists()
    assert (out_dir / "ts4h_factor_asset_summary.csv").exists()
    assert (out_dir / "ts4h_factor_yearly_summary.csv").exists()
    assert (out_dir / "ts4h_factor_bucket_returns.csv").exists()
    assert (out_dir / "ts4h_factor_strategy_summary.csv").exists()
    assert (out_dir / "ts4h_factor_decision_log.md").exists()

    summary = pd.read_csv(out_dir / "ts4h_factor_summary.csv")
    assert {"factor", "family", "strategy_sharpe", "decision"}.issubset(summary.columns)
    assert "ema_gap_120_360" in set(summary["factor"])
