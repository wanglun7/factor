from __future__ import annotations

import pandas as pd

def apply_turnover_cap(current_weights: pd.Series, target_weights: pd.Series, turnover_limit: float) -> pd.Series:
    turnover = float((target_weights - current_weights).abs().sum())
    if turnover <= turnover_limit + 1e-12:
        return target_weights
    alpha = turnover_limit / turnover
    return current_weights + (target_weights - current_weights) * alpha
