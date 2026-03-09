from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from models import BacktestResult


def generate_report(result: BacktestResult) -> dict:
    latest_weights = result.weights.tail(1).fillna(0.0)
    latest_snapshot = latest_weights.iloc[0].sort_values(ascending=False).to_dict() if not latest_weights.empty else {}
    return {
        "state": result.report_state,
        "metrics": {key: round(value, 6) for key, value in result.metrics.items()},
        "latest_weights": {symbol: round(weight, 6) for symbol, weight in latest_snapshot.items() if weight > 0},
        "return_points": len(result.returns),
        "rebalance_points": int((result.turnover > 0).sum()),
    }


def save_report_artifacts(result: BacktestResult, output_dir: str | Path) -> dict:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    report = generate_report(result)
    (target / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    equity_curve = pd.DataFrame(
        {
            "date": result.returns.index,
            "net_return": result.returns.values,
            "gross_return": result.gross_returns.reindex(result.returns.index).values,
            "cost": result.costs.reindex(result.returns.index).values,
            "equity": (1.0 + result.returns.fillna(0.0)).cumprod().values,
        }
    )
    equity_curve.to_csv(target / "equity_curve.csv", index=False)
    result.weights.reset_index().to_csv(target / "weights.csv", index=False)
    result.signal_diagnostics.reset_index().to_csv(target / "signal_diagnostics.csv", index=False)
    return report
