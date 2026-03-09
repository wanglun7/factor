from __future__ import annotations

from pathlib import Path

from strategy import MomentumReversalSignal
from tests.utils import make_csv_dataset, make_panel


def test_signal_prefers_recent_losers_with_strong_intermediate_momentum(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    panel = make_panel(tmp_path)
    signal = MomentumReversalSignal(momentum_lookback=20, reversal_lookback=3, momentum_weight=1.0, reversal_weight=1.0)
    values = signal.compute(panel, panel.dates[-1])

    assert values.notna().all()
    assert values["SOL"] > values["ADA"]
    assert values["AAVE"] > values["BTC"]
