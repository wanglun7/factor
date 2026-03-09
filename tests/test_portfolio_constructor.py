from __future__ import annotations

import pandas as pd

from portfolio.constructor import construct_target_weights


def test_construct_target_weights_builds_long_short_book_with_caps() -> None:
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT"]
    signal = pd.Series(
        {
            "BTC": 0.1,
            "ETH": 0.2,
            "SOL": 2.0,
            "BNB": 1.5,
            "XRP": -1.0,
            "ADA": -1.2,
            "DOGE": -0.7,
            "AVAX": 0.8,
            "LINK": 0.6,
            "DOT": -0.9,
        }
    )
    current_weights = pd.Series(0.0, index=symbols, dtype=float)

    weights = construct_target_weights(
        signal=signal,
        current_weights=current_weights,
        long_n=4,
        short_n=3,
        gross_exposure=1.0,
        net_exposure=0.0,
        max_abs_weight=0.4,
        turnover_limit=10.0,  # disable turnover cap for the unit test
    )

    assert set(weights.index) == set(symbols)
    assert (weights < 0).any()  # short book should exist
    assert float(weights.abs().sum()) <= 1.0 + 1e-9
    assert abs(float(weights.sum()) - 0.0) < 1e-6
    assert float(weights.abs().max()) <= 0.4 + 1e-9


def test_construct_target_weights_applies_turnover_cap() -> None:
    symbols = ["BTC", "ETH", "SOL", "BNB"]
    signal = pd.Series({"BTC": 2.0, "ETH": 1.0, "SOL": -1.0, "BNB": -2.0})
    current_weights = pd.Series({"BTC": 0.25, "ETH": 0.25, "SOL": -0.25, "BNB": -0.25})
    weights = construct_target_weights(
        signal=signal,
        current_weights=current_weights,
        long_n=2,
        short_n=2,
        gross_exposure=1.0,
        net_exposure=0.0,
        max_abs_weight=0.5,
        turnover_limit=0.10,
    )
    assert float((weights - current_weights).abs().sum()) <= 0.10 + 1e-9
