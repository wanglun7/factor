from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app_config import StrategyConfig
from models import AlignedPanel


def _normalize_cross_section(values: pd.Series) -> pd.Series:
    cleaned = values.astype(float).replace([np.inf, -np.inf], np.nan)
    valid = cleaned.dropna()
    if valid.empty:
        return pd.Series(0.0, index=cleaned.index, dtype=float)
    std = float(valid.std(ddof=0))
    if std == 0.0 or np.isnan(std):
        return pd.Series(0.0, index=cleaned.index, dtype=float)
    normalized = (cleaned - float(valid.mean())) / std
    return normalized.fillna(0.0)


@dataclass(frozen=True, slots=True)
class MomentumReversalSignal:
    momentum_lookback: int
    reversal_lookback: int
    momentum_weight: float
    reversal_weight: float
    name: str = "momentum_reversal"

    @classmethod
    def from_config(cls, config: StrategyConfig) -> "MomentumReversalSignal":
        return cls(
            momentum_lookback=config.momentum_lookback,
            reversal_lookback=config.reversal_lookback,
            momentum_weight=config.momentum_weight,
            reversal_weight=config.reversal_weight,
        )

    def compute(self, panel: AlignedPanel, asof_date: pd.Timestamp) -> pd.Series:
        cross_section = panel.cross_section(asof_date)
        momentum = _normalize_cross_section(cross_section[f"ret_{self.momentum_lookback}d"])
        reversal = _normalize_cross_section(-cross_section[f"ret_{self.reversal_lookback}d"])
        combined = momentum * self.momentum_weight + reversal * self.reversal_weight
        denom = abs(self.momentum_weight) + abs(self.reversal_weight)
        if denom > 0:
            combined = combined / denom
        return combined.rename(self.name).sort_index()
