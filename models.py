from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class TSRawDataBundle:
    prices: pd.DataFrame
    spot_prices: pd.DataFrame
    index_prices: pd.DataFrame
    universe_meta: pd.DataFrame
    funding_rates: pd.DataFrame
    open_interest: pd.DataFrame


@dataclass(slots=True)
class AlignedPanel:
    frame: pd.DataFrame

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.frame.index.get_level_values("date").unique()).sort_values()

    @property
    def symbols(self) -> list[str]:
        return sorted(self.frame.index.get_level_values("symbol").unique())

    def history_for_symbol(self, symbol: str) -> pd.DataFrame:
        return self.frame.xs(symbol, level="symbol").copy()
