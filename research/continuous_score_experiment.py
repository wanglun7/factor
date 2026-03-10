from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import ContinuousScoreExperimentConfig, TSUniverseConfig
from models import AlignedPanel
from research.raw_predictors import (
    RawPredictorSpec,
    _build_predictor_frame,
    _catalog,
    _eligible_symbols,
    _forward_return,
    _spread_for_predictor,
)
from research.standardized_scores import _continuous_direction_multiplier, _monotonicity_for_values, _safe_skew


CONTINUOUS_METHODS = (
    "moving_zscore_baseline",
    "ewm_zscore",
    "ts_percentile_rank",
    "level_preserve_clip_scale",
)


def _continuous_specs() -> list[RawPredictorSpec]:
    return [spec for spec in _catalog() if spec.readiness == "implementable" and spec.predictor_type == "continuous"]


def _rolling_clip(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    history = series.shift(1)
    lower = history.rolling(window, min_periods=min_periods).quantile(clip_quantile)
    upper = history.rolling(window, min_periods=min_periods).quantile(1.0 - clip_quantile)
    return series.clip(lower=lower, upper=upper)


def _moving_zscore(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    clipped = _rolling_clip(series, window, min_periods, clip_quantile)
    history = clipped.shift(1)
    mean = history.rolling(window, min_periods=min_periods).mean()
    std = history.rolling(window, min_periods=min_periods).std(ddof=0).replace(0.0, np.nan)
    return ((clipped - mean) / std).replace([np.inf, -np.inf], np.nan)


def _ewm_zscore(series: pd.Series, min_periods: int, clip_quantile: float, span: int) -> pd.Series:
    clipped = _rolling_clip(series, span, min_periods, clip_quantile)
    history = clipped.shift(1)
    mean = history.ewm(span=span, adjust=False, min_periods=min_periods).mean()
    std = history.ewm(span=span, adjust=False, min_periods=min_periods).std(bias=False).replace(0.0, np.nan)
    return ((clipped - mean) / std).replace([np.inf, -np.inf], np.nan)


def _rolling_percentile_rank(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    def percentile_of_last(values: np.ndarray) -> float:
        if len(values) == 0 or np.isnan(values[-1]):
            return np.nan
        valid = values[~np.isnan(values)]
        if len(valid) == 0:
            return np.nan
        return float((valid <= valid[-1]).mean())

    ranked = series.rolling(window, min_periods=min_periods).apply(percentile_of_last, raw=True)
    return ranked * 2.0 - 1.0


def _level_preserve_clip_scale(series: pd.Series, window: int, min_periods: int, clip_quantile: float) -> pd.Series:
    clipped = _rolling_clip(series, window, min_periods, clip_quantile)
    scale = clipped.shift(1).abs().rolling(window, min_periods=min_periods).quantile(1.0 - clip_quantile).replace(0.0, np.nan)
    scaled = clipped / scale
    return scaled.clip(-1.0, 1.0)


def _apply_method(series: pd.Series, method: str, config: ContinuousScoreExperimentConfig) -> pd.Series:
    if method == "moving_zscore_baseline":
        return _moving_zscore(series, config.window, config.min_periods, config.clip_quantile)
    if method == "ewm_zscore":
        return _ewm_zscore(series, config.min_periods, config.clip_quantile, config.ewm_span)
    if method == "ts_percentile_rank":
        return _rolling_percentile_rank(series, config.window, config.min_periods)
    if method == "level_preserve_clip_scale":
        return _level_preserve_clip_scale(series, config.window, config.min_periods, config.clip_quantile)
    raise ValueError(f"Unsupported method: {method}")


def _recommendation_markdown(ranking: pd.DataFrame, gate_diag: pd.DataFrame) -> str:
    lines = ["# Continuous Score Recommendation", ""]
    lines.append("## Best Method By Predictor")
    for row in ranking.sort_values(["family", "predictor"]).itertuples(index=False):
        lines.append(f"- `{row.predictor}` -> `{row.best_method}`")
        lines.append(f"  - reason: ratio={row.best_preservation_ratio:.3f}, monotonicity={row.best_monotonicity_ratio:.2f}, diagnosis={row.gate_diagnosis}")
    lines.append("")
    lines.append("## Gate Diagnosis")
    for row in gate_diag.sort_values(["family", "predictor"]).itertuples(index=False):
        lines.append(f"- `{row.predictor}`: {row.gate_diagnosis}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_continuous_score_experiment_data_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    config: ContinuousScoreExperimentConfig,
) -> dict[str, object]:
    symbols = _eligible_symbols(panel, universe_config)
    if not symbols:
        raise ValueError("No requested symbols are available in the aligned panel.")
    if config.window <= 0 or config.min_periods <= 0 or config.ewm_span <= 0:
        raise ValueError("window, min_periods, and ewm_span must be positive.")
    if config.min_periods > config.window:
        raise ValueError("min_periods cannot exceed window.")
    if not 0.0 < config.clip_quantile < 0.5:
        raise ValueError("clip_quantile must be between 0 and 0.5.")
    return {
        "status": "ok",
        "symbols": symbols,
        "continuous_predictors": [spec.name for spec in _continuous_specs()],
        "methods": list(CONTINUOUS_METHODS),
    }


def run_continuous_score_experiment_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    config: ContinuousScoreExperimentConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    validate_continuous_score_experiment_data_4h(panel, universe_config, config)
    symbols = _eligible_symbols(panel, universe_config)
    specs = _continuous_specs()
    predictor_frame = _build_predictor_frame(panel, symbols).set_index(["date", "symbol"]).sort_index()
    base_frame = predictor_frame.reset_index()
    forward_primary = _forward_return(base_frame, config.primary_horizon, 0)
    delay_1 = _forward_return(base_frame, config.primary_horizon, 1)
    delay_2 = _forward_return(base_frame, config.primary_horizon, 2)

    rows: list[dict[str, object]] = []
    for spec in specs:
        raw_series = predictor_frame[spec.name] * _continuous_direction_multiplier(spec)
        raw_spread = _spread_for_predictor(raw_series, forward_primary, "continuous")
        for method in CONTINUOUS_METHODS:
            score = predictor_frame.groupby(level="symbol")[spec.name].transform(
                lambda values: _apply_method(values * _continuous_direction_multiplier(spec), method, config)
            )
            primary_spread = _spread_for_predictor(score, forward_primary, "continuous")
            delay_1_spread = _spread_for_predictor(score, delay_1, "continuous")
            delay_2_spread = _spread_for_predictor(score, delay_2, "continuous")
            ratio = 0.0 if raw_spread == 0.0 else abs(primary_spread) / abs(raw_spread)
            direction_ok = (raw_spread == 0.0 and primary_spread == 0.0) or (np.sign(primary_spread) == np.sign(raw_spread))
            delay_ok = not ((delay_1_spread * primary_spread) < 0 or (delay_2_spread * primary_spread) < 0)
            monotonicity = _monotonicity_for_values(score, forward_primary, "continuous_score")
            clean = score.dropna()
            rows.append(
                {
                    "predictor": spec.name,
                    "family": spec.family,
                    "method": method,
                    "raw_primary_spread": raw_spread,
                    "score_primary_spread": primary_spread,
                    "spread_preservation_ratio": ratio,
                    "delay_1_spread": delay_1_spread,
                    "delay_2_spread": delay_2_spread,
                    "direction_alignment_ok": direction_ok,
                    "delay_alignment_ok": delay_ok,
                    "monotonicity_ratio": monotonicity,
                    "coverage_ratio": float(score.notna().mean()) if len(score) else 0.0,
                    "mean": float(clean.mean()) if not clean.empty else 0.0,
                    "std": float(clean.std(ddof=0)) if not clean.empty else 0.0,
                    "min": float(clean.min()) if not clean.empty else 0.0,
                    "max": float(clean.max()) if not clean.empty else 0.0,
                    "skew": _safe_skew(clean),
                    "positive_rate": float((score > 0).mean()) if len(score) else 0.0,
                    "negative_rate": float((score < 0).mean()) if len(score) else 0.0,
                }
            )

    summary = pd.DataFrame(rows).sort_values(["family", "predictor", "method"]).reset_index(drop=True)

    ranking_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    for predictor, group in summary.groupby("predictor", sort=True):
        group = group.copy()
        eligible = group.loc[(group["direction_alignment_ok"]) & (group["delay_alignment_ok"])]
        if eligible.empty:
            best = group.sort_values(["spread_preservation_ratio", "monotonicity_ratio", "delay_2_spread"], ascending=[False, False, False]).iloc[0]
        else:
            best = eligible.sort_values(["spread_preservation_ratio", "monotonicity_ratio", "delay_2_spread"], ascending=[False, False, False]).iloc[0]
        max_ratio = float(group["spread_preservation_ratio"].max())
        stable_mid = bool(
            ((group["spread_preservation_ratio"] >= 0.4) & (group["spread_preservation_ratio"] < 0.7) & group["direction_alignment_ok"] & group["delay_alignment_ok"]).any()
        )
        if max_ratio >= 0.7:
            gate_diag = "score_method_problem"
        elif stable_mid:
            gate_diag = "gate_too_strict"
        else:
            gate_diag = "raw_signal_or_family_specific_method_needed"
        ranking_rows.append(
            {
                "predictor": predictor,
                "family": str(best["family"]),
                "best_method": str(best["method"]),
                "best_preservation_ratio": float(best["spread_preservation_ratio"]),
                "best_monotonicity_ratio": float(best["monotonicity_ratio"]),
                "best_delay_2_spread": float(best["delay_2_spread"]),
                "gate_diagnosis": gate_diag,
            }
        )
        gate_rows.append(
            {
                "predictor": predictor,
                "family": str(best["family"]),
                "gate_diagnosis": gate_diag,
                "max_preservation_ratio": max_ratio,
                "any_method_over_0_7": bool(max_ratio >= 0.7),
                "any_stable_mid_band_method": stable_mid,
            }
        )

    ranking = pd.DataFrame(ranking_rows).sort_values(["family", "predictor"]).reset_index(drop=True)
    gate_diag = pd.DataFrame(gate_rows).sort_values(["family", "predictor"]).reset_index(drop=True)
    family_summary = (
        summary.groupby(["family", "method"], as_index=False)[["score_primary_spread", "spread_preservation_ratio", "monotonicity_ratio"]]
        .mean()
        .sort_values(["family", "spread_preservation_ratio", "score_primary_spread"], ascending=[True, False, False])
        .reset_index(drop=True)
    )

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary.to_csv(target / "continuous_score_experiment_summary.csv", index=False)
    ranking.to_csv(target / "continuous_score_method_ranking.csv", index=False)
    family_summary.to_csv(target / "continuous_score_family_summary.csv", index=False)
    gate_diag.to_csv(target / "continuous_score_gate_diagnosis.csv", index=False)
    (target / "continuous_score_recommendation.md").write_text(_recommendation_markdown(ranking, gate_diag), encoding="utf-8")

    return {
        "state": "complete",
        "best_methods": dict(zip(ranking["predictor"], ranking["best_method"])),
        "gate_diagnosis": dict(zip(gate_diag["predictor"], gate_diag["gate_diagnosis"])),
        "artifacts": {
            "summary": "continuous_score_experiment_summary.csv",
            "ranking": "continuous_score_method_ranking.csv",
            "family_summary": "continuous_score_family_summary.csv",
            "gate_diagnosis": "continuous_score_gate_diagnosis.csv",
            "recommendation": "continuous_score_recommendation.md",
        },
    }
