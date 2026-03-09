from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class RawDataBundle:
    prices: pd.DataFrame
    universe_meta: pd.DataFrame


@dataclass(slots=True)
class AlignedPanel:
    frame: pd.DataFrame

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.frame.index.get_level_values("date").unique()).sort_values()

    @property
    def symbols(self) -> list[str]:
        return sorted(self.frame.index.get_level_values("symbol").unique())

    def cross_section(self, asof_date: pd.Timestamp) -> pd.DataFrame:
        return self.frame.xs(pd.Timestamp(asof_date), level="date").copy()

    def history_for_symbol(self, symbol: str) -> pd.DataFrame:
        return self.frame.xs(symbol, level="symbol").copy()


@dataclass(slots=True)
class BacktestResult:
    returns: pd.Series
    gross_returns: pd.Series
    costs: pd.Series
    turnover: pd.Series
    weights: pd.DataFrame
    signal_diagnostics: pd.DataFrame
    metrics: dict[str, float]
    report_state: str
