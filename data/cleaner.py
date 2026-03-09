from __future__ import annotations

import pandas as pd

from models import AlignedPanel, RawDataBundle


def _standardize_dates(frame: pd.DataFrame) -> pd.DataFrame:
    standardized = frame.copy()
    if "date" in standardized.columns:
        standardized["date"] = pd.to_datetime(standardized["date"]).dt.normalize()
    return standardized


def _compute_price_features(prices: pd.DataFrame) -> pd.DataFrame:
    frame = _standardize_dates(prices).sort_values(["symbol", "date"]).reset_index(drop=True)
    frame["dollar_volume"] = frame["close"] * frame["volume"]
    grouped = frame.groupby("symbol", group_keys=False)
    frame["return_1d"] = grouped["close"].pct_change()
    frame["ret_3d"] = grouped["close"].pct_change(3)
    frame["ret_20d"] = grouped["close"].pct_change(20)
    frame["avg_dollar_volume_30d"] = grouped["dollar_volume"].transform(lambda values: values.rolling(30, min_periods=10).mean())
    return frame


def _prepare_meta(universe_meta: pd.DataFrame) -> pd.DataFrame:
    meta = universe_meta.copy()
    meta["listing_date"] = pd.to_datetime(meta["listing_date"]).dt.normalize()
    return meta


def prepare(raw_data: RawDataBundle) -> AlignedPanel:
    prices = _compute_price_features(raw_data.prices)
    meta = _prepare_meta(raw_data.universe_meta)
    merged = prices.merge(meta, on="symbol", how="left")
    merged["days_listed"] = (merged["date"] - merged["listing_date"]).dt.days
    merged = merged.sort_values(["date", "symbol"]).set_index(["date", "symbol"])
    return AlignedPanel(frame=merged)
