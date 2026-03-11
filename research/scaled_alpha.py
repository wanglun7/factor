from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import ScaledAlphaConfig
from research.signal_metrics import forward_return, monotonicity_for_values, rank_metric_for_series, spread_for_predictor


def _bucket_edges(train_values: np.ndarray, bucket_count: int) -> np.ndarray | None:
    if train_values.size < bucket_count or np.unique(train_values).size < 2:
        return None
    quantiles = np.linspace(0.0, 1.0, bucket_count + 1)
    edges = np.quantile(train_values, quantiles)
    edges = np.asarray(edges, dtype=float)
    edges[0] = -np.inf
    edges[-1] = np.inf
    if np.unique(edges).size < 3:
        return None
    return edges


def _forecast_from_history(
    score_history: np.ndarray,
    return_history: np.ndarray,
    current_score: float,
    bucket_count: int,
) -> float:
    edges = _bucket_edges(score_history, bucket_count)
    if edges is None:
        return np.nan
    bucket_ids = np.searchsorted(edges[1:-1], score_history, side="right")
    unique_ids = np.unique(bucket_ids)
    if unique_ids.size < 2:
        return np.nan
    bucket_means = {bucket_id: float(np.mean(return_history[bucket_ids == bucket_id])) for bucket_id in unique_ids}
    current_bucket = int(np.searchsorted(edges[1:-1], current_score, side="right"))
    if current_bucket in bucket_means:
        return bucket_means[current_bucket]
    nearest_bucket = min(unique_ids, key=lambda bucket_id: abs(bucket_id - current_bucket))
    return bucket_means[int(nearest_bucket)]


def _safe_positive_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0 or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)


def _bucket_diagnostics(
    values: pd.Series,
    forward_returns: pd.Series,
    bucket_count: int,
) -> pd.DataFrame:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna()
    if aligned.empty:
        return pd.DataFrame(columns=["bucket", "sample_count", "mean_forward_return", "mean_value"])
    ranked = aligned["value"].rank(method="first")
    try:
        buckets = pd.qcut(ranked, bucket_count, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame(columns=["bucket", "sample_count", "mean_forward_return", "mean_value"])
    aligned["bucket"] = buckets
    if aligned["bucket"].nunique() < 2:
        return pd.DataFrame(columns=["bucket", "sample_count", "mean_forward_return", "mean_value"])
    grouped = (
        aligned.groupby("bucket")
        .agg(
            sample_count=("forward", "size"),
            mean_forward_return=("forward", "mean"),
            mean_value=("value", "mean"),
        )
        .reset_index()
    )
    return grouped


def _autocorr_1(values: pd.Series) -> float:
    valid = values.dropna()
    if len(valid) < 3 or valid.nunique() < 2:
        return 0.0
    result = valid.autocorr(lag=1)
    return 0.0 if pd.isna(result) else float(result)


def _turnover_proxy(values: pd.Series) -> float:
    valid = values.dropna()
    if len(valid) < 2:
        return 0.0
    return float(valid.diff().abs().dropna().mean())


def run_scaled_alpha(
    *,
    composite_panel: pd.DataFrame,
    official_output_name: str,
    base_price_frame: pd.DataFrame,
    config: ScaledAlphaConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    if config.calibration_window != "expanding":
        raise ValueError(f"Unsupported calibration_window: {config.calibration_window}")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    panel = composite_panel.copy()
    required_columns = {"date", "symbol", official_output_name}
    missing = required_columns.difference(panel.columns)
    if missing:
        raise ValueError(f"Composite panel missing required columns for scaled alpha: {sorted(missing)}")

    base_forward = forward_return(base_price_frame, config.primary_horizon, 0).rename("forward_return_30bar")
    source = (
        panel[["date", "symbol", official_output_name]]
        .rename(columns={official_output_name: "composite_score"})
        .set_index(["date", "symbol"])
        .join(base_forward, how="left")
        .reset_index()
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )

    output_frames: list[pd.DataFrame] = []
    for _, symbol_frame in source.groupby("symbol", sort=True):
        symbol_frame = symbol_frame.copy().reset_index(drop=True)
        forecasts: list[float] = []
        scaled: list[float] = []
        for idx, row in symbol_frame.iterrows():
            history = symbol_frame.iloc[:idx]
            history = history.dropna(subset=["composite_score", "forward_return_30bar"])
            if len(history) < config.min_train_points:
                forecasts.append(np.nan)
                scaled.append(np.nan)
                continue
            score_history = history["composite_score"].to_numpy(dtype=float)
            return_history = history["forward_return_30bar"].to_numpy(dtype=float)
            forecast = _forecast_from_history(
                score_history=score_history,
                return_history=return_history,
                current_score=float(row["composite_score"]),
                bucket_count=config.bucket_count,
            )
            forecasts.append(forecast)
            valid_forecasts = np.array([value for value in forecasts[:-1] if pd.notna(value)], dtype=float)
            if pd.isna(forecast) or valid_forecasts.size < max(10, config.bucket_count):
                scaled.append(np.nan)
                continue
            scale_ref = float(np.quantile(np.abs(valid_forecasts), config.scale_quantile))
            if scale_ref <= 0.0 or pd.isna(scale_ref):
                scaled.append(np.nan)
                continue
            scaled_value = float(np.clip(forecast / scale_ref, config.clip_min, config.clip_max))
            scaled.append(scaled_value)
        symbol_frame["forecast_return_30bar"] = forecasts
        symbol_frame["scaled_alpha"] = scaled
        output_frames.append(symbol_frame)

    series = pd.concat(output_frames, ignore_index=True).sort_values(["date", "symbol"]).reset_index(drop=True)
    series["source_name"] = official_output_name
    series = series[["date", "symbol", "source_name", "composite_score", "forecast_return_30bar", "scaled_alpha"]]

    series.to_parquet(target / "scaled_alpha_series.parquet", index=False)

    valid_forecasts = series["forecast_return_30bar"].dropna()
    valid_scaled = series["scaled_alpha"].dropna()
    forward_series = source.set_index(["date", "symbol"])["forward_return_30bar"]
    composite_series = series.set_index(["date", "symbol"])["composite_score"]
    forecast_series = series.set_index(["date", "symbol"])["forecast_return_30bar"]
    scaled_series = series.set_index(["date", "symbol"])["scaled_alpha"]

    composite_rank_metric = rank_metric_for_series(composite_series, forward_series)
    forecast_rank_metric = rank_metric_for_series(forecast_series, forward_series)
    scaled_rank_metric = rank_metric_for_series(scaled_series, forward_series)
    bucket_table = _bucket_diagnostics(scaled_series, forward_series, config.bucket_count)
    forecast_bucket_monotonicity = (
        monotonicity_for_values(scaled_series, forward_series, "continuous") if not bucket_table.empty else 0.0
    )
    forecast_bucket_spread = spread_for_predictor(scaled_series, forward_series, "continuous")
    bounded_output_ok = bool(valid_scaled.empty or ((valid_scaled >= config.clip_min) & (valid_scaled <= config.clip_max)).all())
    min_live_coverage_ok = bool(series["scaled_alpha"].notna().mean() >= 0.75) if not series.empty else False
    clip_rate = float(valid_scaled.abs().ge(max(abs(config.clip_min), abs(config.clip_max))).mean()) if not valid_scaled.empty else 0.0
    scaled_alpha_sign_balance = float(
        valid_scaled.gt(0).mean() - valid_scaled.lt(0).mean()
    ) if not valid_scaled.empty else 0.0
    forecast_zero_crossing_rate = float(
        np.mean(np.sign(valid_forecasts.to_numpy(dtype=float)[1:]) != np.sign(valid_forecasts.to_numpy(dtype=float)[:-1]))
    ) if len(valid_forecasts) > 1 else 0.0
    composite_to_scaled_rank_retention = _safe_positive_ratio(scaled_rank_metric, composite_rank_metric)
    forecast_to_scaled_rank_retention = _safe_positive_ratio(scaled_rank_metric, forecast_rank_metric)
    composite_vs_scaled_direction_match = bool(
        (composite_rank_metric == 0.0 and scaled_rank_metric == 0.0)
        or (np.sign(composite_rank_metric) == np.sign(scaled_rank_metric))
    )

    strong_pass = (
        scaled_rank_metric > 0.0
        and composite_to_scaled_rank_retention >= 0.80
        and forecast_bucket_monotonicity >= 0.60
        and float(series["scaled_alpha"].notna().mean()) >= 0.75
        and clip_rate <= 0.05
    )
    conditional_pass = (
        scaled_rank_metric > 0.0
        and composite_to_scaled_rank_retention >= 0.60
        and forecast_bucket_monotonicity >= 0.50
        and float(series["scaled_alpha"].notna().mean()) >= 0.60
        and clip_rate <= 0.10
    )
    verdict = "strong_pass" if strong_pass else "conditional_pass" if conditional_pass else "fail"

    summary = pd.DataFrame(
        [
            {
                "source_name": official_output_name,
                "calibration_window": config.calibration_window,
                "bucket_count": config.bucket_count,
                "coverage_ratio": float(series["scaled_alpha"].notna().mean()) if not series.empty else 0.0,
                "forecast_mean": float(valid_forecasts.mean()) if not valid_forecasts.empty else 0.0,
                "forecast_abs_p95": float(np.quantile(np.abs(valid_forecasts), 0.95)) if not valid_forecasts.empty else 0.0,
                "scaled_alpha_mean": float(valid_scaled.mean()) if not valid_scaled.empty else 0.0,
                "scaled_alpha_std": float(valid_scaled.std(ddof=0)) if len(valid_scaled) > 1 else 0.0,
                "scaled_alpha_clip_rate": clip_rate,
                "composite_score_rank_metric": composite_rank_metric,
                "forecast_return_rank_metric": forecast_rank_metric,
                "scaled_alpha_rank_metric": scaled_rank_metric,
                "composite_to_scaled_rank_retention": composite_to_scaled_rank_retention,
                "forecast_to_scaled_rank_retention": forecast_to_scaled_rank_retention,
                "composite_vs_scaled_direction_match": composite_vs_scaled_direction_match,
                "forecast_bucket_monotonicity": forecast_bucket_monotonicity,
                "forecast_bucket_spread": forecast_bucket_spread,
                "forecast_zero_crossing_rate": forecast_zero_crossing_rate,
                "scaled_alpha_sign_balance": scaled_alpha_sign_balance,
                "scaled_alpha_autocorr_1": _autocorr_1(valid_scaled),
                "scaled_alpha_turnover_proxy": _turnover_proxy(valid_scaled),
                "bounded_output_ok": bounded_output_ok,
                "min_live_coverage_ok": min_live_coverage_ok,
                "verdict": verdict,
            }
        ]
    )
    summary.to_csv(target / "scaled_alpha_summary.csv", index=False)
    bucket_table.insert(0, "source_name", official_output_name)
    bucket_table.to_csv(target / "scaled_alpha_bucket_diagnostics.csv", index=False)
    summary.to_csv(target / "scaled_alpha_evaluation.csv", index=False)

    decision_log = "\n".join(
        [
            "# Scaled Alpha Decision Log",
            "",
            f"- source_name: `{official_output_name}`",
            f"- calibration_window: `{config.calibration_window}`",
            f"- bucket_count: `{config.bucket_count}`",
            f"- min_train_points: `{config.min_train_points}`",
            f"- scale_quantile: `{config.scale_quantile}`",
            f"- coverage_ratio: `{summary.loc[0, 'coverage_ratio']:.4f}`",
            f"- forecast_mean: `{summary.loc[0, 'forecast_mean']:.6f}`",
            f"- forecast_abs_p95: `{summary.loc[0, 'forecast_abs_p95']:.6f}`",
            f"- scaled_alpha_mean: `{summary.loc[0, 'scaled_alpha_mean']:.6f}`",
            f"- scaled_alpha_std: `{summary.loc[0, 'scaled_alpha_std']:.6f}`",
            f"- scaled_alpha_clip_rate: `{summary.loc[0, 'scaled_alpha_clip_rate']:.4f}`",
            "",
        ]
    )
    (target / "scaled_alpha_decision_log.md").write_text(decision_log, encoding="utf-8")

    evaluation_log = "\n".join(
        [
            "# Scaled Alpha Evaluation Log",
            "",
            f"- source_name: `{official_output_name}`",
            f"- verdict: `{verdict}`",
            f"- composite_score_rank_metric: `{composite_rank_metric:.6f}`",
            f"- scaled_alpha_rank_metric: `{scaled_rank_metric:.6f}`",
            f"- composite_to_scaled_rank_retention: `{composite_to_scaled_rank_retention:.4f}`",
            f"- forecast_bucket_monotonicity: `{forecast_bucket_monotonicity:.4f}`",
            f"- forecast_bucket_spread: `{forecast_bucket_spread:.6f}`",
            f"- bounded_output_ok: `{bounded_output_ok}`",
            f"- min_live_coverage_ok: `{min_live_coverage_ok}`",
            "",
        ]
    )
    (target / "scaled_alpha_evaluation_log.md").write_text(evaluation_log, encoding="utf-8")

    return {
        "series": series,
        "summary": summary,
        "source_name": official_output_name,
        "verdict": verdict,
        "artifacts": {
            "scaled_alpha_series": "scaled_alpha_series.parquet",
            "scaled_alpha_summary": "scaled_alpha_summary.csv",
            "scaled_alpha_decision_log": "scaled_alpha_decision_log.md",
            "scaled_alpha_evaluation": "scaled_alpha_evaluation.csv",
            "scaled_alpha_bucket_diagnostics": "scaled_alpha_bucket_diagnostics.csv",
            "scaled_alpha_evaluation_log": "scaled_alpha_evaluation_log.md",
        },
    }
