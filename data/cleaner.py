from __future__ import annotations

import numpy as np
import pandas as pd

from models import AlignedPanel, TSRawDataBundle


BARS_PER_DAY = 6
ANNUALIZATION = BARS_PER_DAY * 365


def _standardize_dates(frame: pd.DataFrame) -> pd.DataFrame:
    standardized = frame.copy()
    if "date" in standardized.columns:
        standardized["date"] = pd.to_datetime(standardized["date"], utc=True, errors="coerce").dt.tz_convert(None)
    return standardized


def _compute_price_features(prices: pd.DataFrame) -> pd.DataFrame:
    frame = _standardize_dates(prices).sort_values(["symbol", "date"]).reset_index(drop=True)
    frame["dollar_volume"] = frame["close"] * frame["volume"]
    grouped = frame.groupby("symbol", group_keys=False)

    frame["lag_close"] = grouped["close"].shift(1)
    frame["lag_dollar_volume"] = grouped["dollar_volume"].shift(1)
    frame["ret_1bar"] = grouped["lag_close"].pct_change(fill_method=None)
    frame["ret_6bar"] = frame["lag_close"] / grouped["lag_close"].shift(6) - 1.0
    frame["ret_18bar"] = frame["lag_close"] / grouped["lag_close"].shift(18) - 1.0
    frame["ret_30bar"] = frame["lag_close"] / grouped["lag_close"].shift(30) - 1.0
    frame["ret_120bar"] = frame["lag_close"] / grouped["lag_close"].shift(120) - 1.0
    frame["ret_360bar"] = frame["lag_close"] / grouped["lag_close"].shift(360) - 1.0
    frame["next_return_1bar"] = grouped["close"].shift(-1) / frame["close"] - 1.0
    frame["realized_vol_30bar"] = grouped["ret_1bar"].transform(lambda values: values.rolling(30, min_periods=30).std(ddof=0) * np.sqrt(ANNUALIZATION))
    frame["realized_vol_120bar"] = grouped["ret_1bar"].transform(lambda values: values.rolling(120, min_periods=120).std(ddof=0) * np.sqrt(ANNUALIZATION))
    frame["avg_dollar_volume_30bar"] = grouped["lag_dollar_volume"].transform(lambda values: values.rolling(30, min_periods=30).mean())
    frame["avg_dollar_volume_120bar"] = grouped["lag_dollar_volume"].transform(lambda values: values.rolling(120, min_periods=120).mean())
    frame["ema_120"] = grouped["close"].transform(lambda values: values.shift(1).ewm(span=120, adjust=False, min_periods=120).mean())
    frame["ema_360"] = grouped["close"].transform(lambda values: values.shift(1).ewm(span=360, adjust=False, min_periods=360).mean())
    frame["rolling_max_360bar"] = grouped["close"].transform(lambda values: values.shift(1).rolling(360, min_periods=360).max())
    frame["rolling_min_360bar"] = grouped["close"].transform(lambda values: values.shift(1).rolling(360, min_periods=360).min())
    frame["breakout_360bar"] = frame["lag_close"] / frame["rolling_max_360bar"] - frame["lag_close"] / frame["rolling_min_360bar"]
    frame["up_bar_count_30"] = grouped["ret_1bar"].transform(lambda values: values.gt(0).rolling(30, min_periods=30).sum())
    frame["down_bar_count_30"] = grouped["ret_1bar"].transform(lambda values: values.lt(0).rolling(30, min_periods=30).sum())
    frame["amihud_raw"] = frame["ret_1bar"].abs() / frame["lag_dollar_volume"].replace(0.0, np.nan)
    frame["amihud_30bar"] = grouped["amihud_raw"].transform(lambda values: values.rolling(30, min_periods=30).mean())
    frame["amihud_120bar"] = grouped["amihud_raw"].transform(lambda values: values.rolling(120, min_periods=120).mean())
    return frame.drop(columns=["amihud_raw"])


def _prepare_meta(universe_meta: pd.DataFrame) -> pd.DataFrame:
    meta = universe_meta.copy()
    meta["listing_date"] = pd.to_datetime(meta["listing_date"], utc=True, errors="coerce").dt.tz_convert(None)
    return meta


def _prepare_reference_prices(price_dates: pd.DataFrame, frame: pd.DataFrame, column_name: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "symbol", column_name])
    reference = _standardize_dates(frame)
    reference[column_name] = pd.to_numeric(reference["close"], errors="coerce")
    reference = reference.groupby(["date", "symbol"], as_index=False)[column_name].mean()
    return _align_asof(price_dates, reference, [column_name])


def _align_asof(price_dates: pd.DataFrame, raw_series: pd.DataFrame, value_columns: list[str]) -> pd.DataFrame:
    if raw_series.empty:
        return pd.DataFrame(columns=["date", "symbol", *value_columns])
    left = price_dates.sort_values(["symbol", "date"]).reset_index(drop=True)
    right = _standardize_dates(raw_series).sort_values(["symbol", "date"]).reset_index(drop=True)
    aligned_parts: list[pd.DataFrame] = []
    for symbol, left_group in left.groupby("symbol", sort=False):
        right_group = right.loc[right["symbol"] == symbol, ["date", "symbol", *value_columns]].copy()
        if right_group.empty:
            continue
        aligned = pd.merge_asof(
            left_group.sort_values("date"),
            right_group.sort_values("date"),
            on="date",
            by="symbol",
            direction="backward",
        )
        aligned_parts.append(aligned)
    if not aligned_parts:
        return pd.DataFrame(columns=["date", "symbol", *value_columns])
    return pd.concat(aligned_parts, ignore_index=True)


def _prepare_funding(price_dates: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "symbol",
                "funding_rate_8h",
                "funding_rate_lag1",
                "avg_funding_21period",
                "avg_funding_90period",
            ]
        )
    funding = _standardize_dates(frame)
    funding["funding_rate_8h"] = pd.to_numeric(funding["funding_rate"], errors="coerce")
    funding = funding.groupby(["date", "symbol"], as_index=False)["funding_rate_8h"].mean()
    funding = funding.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = funding.groupby("symbol", group_keys=False)
    funding["funding_rate_lag1"] = grouped["funding_rate_8h"].shift(1)
    funding["avg_funding_21period"] = grouped["funding_rate_lag1"].transform(lambda values: values.rolling(21, min_periods=9).mean())
    funding["avg_funding_90period"] = grouped["funding_rate_lag1"].transform(lambda values: values.rolling(90, min_periods=30).mean())
    return _align_asof(
        price_dates,
        funding,
        ["funding_rate_8h", "funding_rate_lag1", "avg_funding_21period", "avg_funding_90period"],
    )


def _prepare_open_interest(price_dates: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "symbol", "open_interest", "oi_change_21period"])
    oi = _standardize_dates(frame)
    oi["open_interest"] = pd.to_numeric(oi["open_interest"], errors="coerce")
    oi = oi.groupby(["date", "symbol"], as_index=False)["open_interest"].mean()
    oi = oi.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = oi.groupby("symbol", group_keys=False)
    oi["open_interest_lag1"] = grouped["open_interest"].shift(1)
    oi["oi_change_21period"] = oi["open_interest_lag1"] / grouped["open_interest_lag1"].shift(21) - 1.0
    return _align_asof(price_dates, oi.drop(columns=["open_interest_lag1"]), ["open_interest", "oi_change_21period"])


def prepare(raw_data: TSRawDataBundle) -> AlignedPanel:
    prices = _compute_price_features(raw_data.prices)
    meta = _prepare_meta(raw_data.universe_meta)
    price_dates = prices[["date", "symbol"]].copy()
    spot = _prepare_reference_prices(price_dates, raw_data.spot_prices, "spot_close")
    index_prices = _prepare_reference_prices(price_dates, raw_data.index_prices, "index_close")
    funding = _prepare_funding(price_dates, raw_data.funding_rates)
    open_interest = _prepare_open_interest(price_dates, raw_data.open_interest)

    merged = prices.merge(meta, on="symbol", how="left")
    if not spot.empty:
        merged = merged.merge(spot, on=["date", "symbol"], how="left")
    else:
        merged["spot_close"] = np.nan
    if not index_prices.empty:
        merged = merged.merge(index_prices, on=["date", "symbol"], how="left")
    else:
        merged["index_close"] = np.nan
    if not funding.empty:
        merged = merged.merge(funding, on=["date", "symbol"], how="left")
    else:
        merged["funding_rate_8h"] = np.nan
        merged["funding_rate_lag1"] = np.nan
        merged["avg_funding_21period"] = np.nan
        merged["avg_funding_90period"] = np.nan
    if not open_interest.empty:
        merged = merged.merge(open_interest, on=["date", "symbol"], how="left")
    else:
        merged["open_interest"] = np.nan
        merged["oi_change_21period"] = np.nan
    merged["days_listed"] = (merged["date"] - merged["listing_date"]).dt.days
    merged = merged.sort_values(["date", "symbol"]).set_index(["date", "symbol"])
    return AlignedPanel(frame=merged)
