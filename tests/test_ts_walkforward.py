from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_ts_walkforward_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_ts_walkforward_4h_writes_expected_artifacts(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    panel = make_panel(tmp_path)

    report = run_ts_walkforward_4h(
        panel=panel,
        universe_config=config.ts_universe,
        research_config=config.ts_research,
        backtest_config=config.ts_backtest,
        output_dir=tmp_path / "ts4h_walkforward",
    )

    assert report["state"] == "complete"
    out_dir = tmp_path / "ts4h_walkforward"
    assert (out_dir / "ts4h_walkforward_splits.csv").exists()
    assert (out_dir / "ts4h_walkforward_summary.csv").exists()

    summary = pd.read_csv(out_dir / "ts4h_walkforward_summary.csv")
    assert {"factor", "mean_test_return", "mean_test_sharpe"}.issubset(summary.columns)
