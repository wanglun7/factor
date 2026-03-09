from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio.risk import apply_turnover_cap


def _softmax(values: pd.Series) -> pd.Series:
    centered = values - values.max()
    exp_values = np.exp(centered)
    total = exp_values.sum()
    if total == 0 or np.isnan(total):
        return pd.Series(1.0 / len(values), index=values.index)
    return exp_values / total


def _bounded_allocate_total(base_scores: pd.Series, total: float, max_abs_weight: float) -> pd.Series:
    weights = pd.Series(0.0, index=base_scores.index, dtype=float)
    remaining = float(total)
    if total <= 0 or len(weights) == 0:
        return weights

    base_probs = _softmax(base_scores)
    room = pd.Series(float(max_abs_weight), index=weights.index, dtype=float)
    open_symbols = room[room > 1e-12].index.tolist()

    while remaining > 1e-12 and open_symbols:
        probs = base_probs.reindex(open_symbols).fillna(0.0)
        if probs.sum() == 0:
            probs = pd.Series(1.0 / len(open_symbols), index=open_symbols)
        else:
            probs = probs / probs.sum()
        tentative = probs * remaining
        addition = tentative.clip(upper=room.reindex(open_symbols))
        weights.loc[open_symbols] += addition
        remaining -= float(addition.sum())
        room = (float(max_abs_weight) - weights).clip(lower=0.0)
        open_symbols = room[room > 1e-12].index.tolist()

    return weights


def construct_target_weights(
    signal: pd.Series,
    current_weights: pd.Series,
    long_n: int,
    short_n: int,
    gross_exposure: float,
    net_exposure: float,
    max_abs_weight: float,
    turnover_limit: float,
) -> pd.Series:
    if gross_exposure < abs(net_exposure) - 1e-12:
        raise ValueError("gross_exposure must be >= abs(net_exposure).")
    long_total = 0.5 * (gross_exposure + net_exposure)
    short_total = 0.5 * (gross_exposure - net_exposure)

    universe_signal = signal.reindex(current_weights.index).dropna().sort_values(ascending=False)
    if universe_signal.empty:
        return current_weights * 0.0

    selected_long = list(universe_signal.head(int(long_n)).index)
    selected_long_scores = universe_signal.reindex(selected_long).dropna()

    remaining = universe_signal.index.difference(pd.Index(selected_long_scores.index))
    selected_short = list(universe_signal.reindex(remaining).sort_values(ascending=True).head(int(short_n)).index)
    selected_short_scores = universe_signal.reindex(selected_short).dropna()

    long_weights = _bounded_allocate_total(
        base_scores=selected_long_scores,
        total=float(long_total),
        max_abs_weight=float(max_abs_weight),
    )

    short_abs = pd.Series(dtype=float)
    if short_total > 1e-12 and not selected_short_scores.empty:
        short_scores = (-selected_short_scores).rename("short_scores")
        short_abs = _bounded_allocate_total(
            base_scores=short_scores,
            total=float(short_total),
            max_abs_weight=float(max_abs_weight),
        )

    target = pd.Series(0.0, index=current_weights.index, dtype=float)
    target.loc[long_weights.index] = long_weights
    if not short_abs.empty:
        target.loc[short_abs.index] = -short_abs

    target = apply_turnover_cap(current_weights, target, turnover_limit)
    return target.reindex(current_weights.index).fillna(0.0)
