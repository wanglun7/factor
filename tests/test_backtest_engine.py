from __future__ import annotations

import json
from pathlib import Path

from backtest.report import save_report_artifacts
from tests.utils import make_backtest_result, make_csv_dataset


def test_backtest_runs_and_persists_phase1_artifacts(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "artifacts"
    make_csv_dataset(data_dir)
    result = make_backtest_result(data_dir)
    report = save_report_artifacts(result, output_dir)

    assert result.report_state == "complete"
    assert set(["annual_return", "sharpe", "rank_ic_mean"]).issubset(result.metrics)
    assert (output_dir / "report.json").exists()
    assert (output_dir / "equity_curve.csv").exists()
    assert (output_dir / "weights.csv").exists()
    assert (output_dir / "signal_diagnostics.csv").exists()
    parsed = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert parsed["state"] == "complete"
