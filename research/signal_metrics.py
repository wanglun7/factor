from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return(frame: pd.DataFrame, horizon: int, delay: int) -> pd.Series:
    close = frame.pivot(index="date", columns="symbol", values="close").sort_index()
    forward = close.shift(-(horizon + delay)) / close.shift(-delay) - 1.0
    try:
        series = forward.stack(future_stack=True)
    except TypeError:
        series = forward.stack(dropna=False)
    series.name = f"forward_{horizon}bar_delay_{delay}"
    return series


def spread_for_predictor(values: pd.Series, forward_returns: pd.Series, predictor_type: str) -> float:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna()
    if aligned.empty:
        return 0.0
    if predictor_type == "continuous":
        ranked = aligned["value"].rank(method="first")
        try:
            buckets = pd.qcut(ranked, 5, labels=False, duplicates="drop")
        except ValueError:
            return 0.0
        aligned["bucket"] = buckets
        if aligned["bucket"].nunique() < 2:
            return 0.0
        grouped = aligned.groupby("bucket")["forward"].mean()
        return float(grouped.max() - grouped.min())
    unique_values = sorted(set(aligned["value"].dropna().tolist()))
    if predictor_type == "binary_rule":
        unique = set(unique_values)
        if {0.0, 1.0}.issubset(unique):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == 0.0, "forward"].mean())
        if {-1.0, 1.0}.issubset(unique):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == -1.0, "forward"].mean())
        return 0.0
    if predictor_type == "ternary_rule":
        unique = set(unique_values)
        if {-1.0, 1.0}.issubset(unique):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == -1.0, "forward"].mean())
        if {0.0, 1.0}.issubset(unique):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == 0.0, "forward"].mean())
        return 0.0
    raise ValueError(f"Unsupported predictor_type: {predictor_type}")


def monotonicity_for_values(values: pd.Series, forward_returns: pd.Series, predictor_type: str) -> float:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna()
    if aligned.empty:
        return 0.0
    if predictor_type == "continuous":
        ranked = aligned["value"].rank(method="first")
        try:
            buckets = pd.qcut(ranked, 5, labels=False, duplicates="drop")
        except ValueError:
            return 0.0
        aligned["bucket"] = buckets
        if aligned["bucket"].nunique() < 2:
            return 0.0
        grouped = aligned.groupby("bucket")["forward"].mean()
        diffs = grouped.diff().dropna()
        if diffs.empty:
            return 0.0
        return float((diffs > 0).mean())
    grouped = aligned.groupby("value")["forward"].mean().sort_index()
    if len(grouped) < 2:
        return 0.0
    diffs = grouped.diff().dropna()
    if diffs.empty:
        return 0.0
    return float((diffs > 0).mean())


def rank_metric_for_series(values: pd.Series, forward_returns: pd.Series) -> float:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna().sort_index()
    if aligned.empty or aligned["value"].nunique() < 2 or aligned["forward"].nunique() < 2:
        return 0.0
    corr = aligned["value"].corr(aligned["forward"], method="spearman")
    return 0.0 if pd.isna(corr) else float(corr)


def rank_metric_with_block_bootstrap(
    values: pd.Series,
    forward_returns: pd.Series,
    *,
    block_size: int,
    n_boot: int,
    seed: int,
) -> tuple[float, float, float]:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna().sort_index()
    if aligned.empty or aligned["value"].nunique() < 2 or aligned["forward"].nunique() < 2:
        return 0.0, 0.0, 0.0

    point = rank_metric_for_series(aligned["value"], aligned["forward"])
    n_obs = len(aligned)
    if n_obs < 4 or n_boot <= 1:
        return point, point, point

    effective_block = max(1, min(block_size, n_obs))
    max_start = max(1, n_obs - effective_block + 1)
    rng = np.random.default_rng(seed)
    values_array = aligned["value"].to_numpy()
    forward_array = aligned["forward"].to_numpy()
    boot_metrics: list[float] = []
    for _ in range(n_boot):
        sampled_indices: list[int] = []
        while len(sampled_indices) < n_obs:
            start = int(rng.integers(0, max_start))
            sampled_indices.extend(range(start, start + effective_block))
        sampled = np.array(sampled_indices[:n_obs], dtype=int)
        sample_value = pd.Series(values_array[sampled])
        sample_forward = pd.Series(forward_array[sampled])
        boot_metrics.append(rank_metric_for_series(sample_value, sample_forward))
    lower, upper = np.quantile(np.array(boot_metrics, dtype=float), [0.025, 0.975])
    return point, float(lower), float(upper)


def stability_score(delay_0: float, delay_1: float, delay_2: float) -> float:
    if delay_0 <= 0.0:
        return 0.0
    return float(np.mean([delay_1, delay_2]) / delay_0)
