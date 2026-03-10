from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_clip(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    history = series.shift(1)
    lower = history.rolling(window, min_periods=min_periods).quantile(clip_quantile)
    upper = history.rolling(window, min_periods=min_periods).quantile(1.0 - clip_quantile)
    return series.clip(lower=lower, upper=upper)


def moving_zscore(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    clipped = rolling_clip(series, window, min_periods, clip_quantile)
    history = clipped.shift(1)
    mean = history.rolling(window, min_periods=min_periods).mean()
    std = history.rolling(window, min_periods=min_periods).std(ddof=0).replace(0.0, np.nan)
    return ((clipped - mean) / std).replace([np.inf, -np.inf], np.nan)


def ewm_zscore(series: pd.Series, min_periods: int, clip_quantile: float, span: int) -> pd.Series:
    clipped = rolling_clip(series, span, min_periods, clip_quantile)
    history = clipped.shift(1)
    mean = history.ewm(span=span, adjust=False, min_periods=min_periods).mean()
    std = history.ewm(span=span, adjust=False, min_periods=min_periods).std(bias=False).replace(0.0, np.nan)
    return ((clipped - mean) / std).replace([np.inf, -np.inf], np.nan)


def rolling_percentile_rank(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    def percentile_of_last(values: np.ndarray) -> float:
        if len(values) == 0 or np.isnan(values[-1]):
            return np.nan
        valid = values[~np.isnan(values)]
        if len(valid) == 0:
            return np.nan
        return float((valid <= valid[-1]).mean())

    ranked = series.rolling(window, min_periods=min_periods).apply(percentile_of_last, raw=True)
    return ranked * 2.0 - 1.0


def level_preserve_clip_scale(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    clipped = rolling_clip(series, window, min_periods, clip_quantile)
    scale = clipped.shift(1).abs().rolling(window, min_periods=min_periods).quantile(1.0 - clip_quantile).replace(0.0, np.nan)
    scaled = clipped / scale
    return scaled.clip(-1.0, 1.0)


def apply_continuous_method(
    series: pd.Series,
    method: str,
    *,
    window: int,
    min_periods: int,
    clip_quantile: float,
    ewm_span: int,
) -> pd.Series:
    if method == "moving_zscore_baseline":
        return moving_zscore(series, window, min_periods, clip_quantile)
    if method == "ewm_zscore":
        return ewm_zscore(series, min_periods, clip_quantile, ewm_span)
    if method == "ts_percentile_rank":
        return rolling_percentile_rank(series, window, min_periods)
    if method == "level_preserve_clip_scale":
        return level_preserve_clip_scale(series, window, min_periods, clip_quantile)
    raise ValueError(f"Unsupported method: {method}")
