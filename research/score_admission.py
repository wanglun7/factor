from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import ScoreAdmissionConfig
from research.continuous_score_methods import apply_continuous_method
from research.signal_metrics import (
    forward_return,
    monotonicity_for_values,
    rank_metric_for_series,
    spread_for_predictor,
)


def _continuous_method(score_method_family: object) -> str:
    if score_method_family == "return_based":
        return "ts_percentile_rank"
    if score_method_family == "basis_like":
        return "level_preserve_clip_scale"
    return "ewm_zscore"


def _direction_multiplier(alpha_direction_policy: object) -> float:
    return -1.0 if alpha_direction_policy == "negate" else 1.0


def _build_integrity_score_series(raw_values: pd.Series, row: pd.Series, config: ScoreAdmissionConfig) -> tuple[pd.Series, str]:
    predictor_type = str(row["predictor_type"])
    if predictor_type == "binary_rule":
        return raw_values.map({1.0: 1.0, 0.0: -1.0}), "binary_rule_signed_mapping"
    if predictor_type == "ternary_rule":
        return raw_values, "ternary_rule_identity"
    method = _continuous_method(row.get("score_method_family"))
    direction = _direction_multiplier(row.get("alpha_direction_policy"))
    values = raw_values.groupby(level=1, group_keys=False).transform(
        lambda series: apply_continuous_method(
            series * direction,
            method,
            window=config.z_window,
            min_periods=config.z_min_periods,
            clip_quantile=config.clip_quantile,
            ewm_span=config.ewm_span,
        )
    )
    return values, method


def _build_composite_ready_score_series(score_values: pd.Series, config: ScoreAdmissionConfig) -> pd.Series:
    return score_values.groupby(level=1, group_keys=False).transform(
        lambda series: apply_continuous_method(
            series,
            "ts_percentile_rank",
            window=config.z_window,
            min_periods=config.z_min_periods,
            clip_quantile=config.clip_quantile,
            ewm_span=config.ewm_span,
        )
    )


def _integrity_gate(
    predictor_type: str,
    raw_primary_spread: float,
    integrity_primary_spread: float,
    delay_1_spread: float,
    delay_2_spread: float,
    monotonicity: float,
    distribution_ok: bool,
    config: ScoreAdmissionConfig,
) -> tuple[str, list[str], float, bool, bool]:
    ratio = 0.0 if raw_primary_spread == 0.0 else abs(integrity_primary_spread) / abs(raw_primary_spread)
    direction_ok = (raw_primary_spread == 0.0 and integrity_primary_spread == 0.0) or (
        np.sign(raw_primary_spread) == np.sign(integrity_primary_spread)
    )
    delay_ok = not ((delay_1_spread * integrity_primary_spread) < 0 or (delay_2_spread * integrity_primary_spread) < 0)
    failures: list[str] = []
    if not direction_ok:
        failures.append("direction_mismatch")
    if not delay_ok:
        failures.append("delay_sign_flip")
    if not distribution_ok:
        failures.append("distribution_invalid")
    if predictor_type in {"binary_rule", "ternary_rule"}:
        if ratio < config.rule_integrity_spread_gate:
            failures.append("spread_decay_excessive")
        return ("strong" if not failures else "fail"), failures or ["passed"], ratio, direction_ok, delay_ok
    if ratio >= config.continuous_strong_spread_gate and monotonicity >= config.continuous_conditional_monotonicity_gate and not failures:
        return "strong", ["passed"], ratio, direction_ok, delay_ok
    if ratio >= config.continuous_conditional_spread_gate and monotonicity >= config.continuous_conditional_monotonicity_gate and not failures:
        return "conditional", ["passed"], ratio, direction_ok, delay_ok
    if ratio < config.continuous_conditional_spread_gate:
        failures.append("spread_decay_excessive")
    if monotonicity < config.continuous_conditional_monotonicity_gate:
        failures.append("monotonicity_too_low")
    return "fail", failures, ratio, direction_ok, delay_ok


def run_score_admission(
    raw_catalog: pd.DataFrame,
    raw_frame: pd.DataFrame,
    config: ScoreAdmissionConfig,
    output_dir: str | Path,
) -> dict[str, pd.DataFrame]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    base_frame = raw_frame.reset_index()
    forward_0 = forward_return(base_frame, config.primary_horizon, 0)
    forward_1 = forward_return(base_frame, config.primary_horizon, 1)
    forward_2 = forward_return(base_frame, config.primary_horizon, 2)

    score_columns: dict[str, pd.Series] = {}
    rows: list[dict[str, object]] = []
    for row_dict in raw_catalog.to_dict("records"):
        row = pd.Series(row_dict)
        source_name = str(row["name"])
        predictor_type = str(row["predictor_type"])
        integrity_score_name = f"{source_name}_integrity_score"
        score_name = f"{source_name}_score"

        raw_values = raw_frame[source_name]
        integrity_values, selected_method = _build_integrity_score_series(raw_values, row, config)
        composite_ready_values = _build_composite_ready_score_series(integrity_values, config)

        score_columns[integrity_score_name] = integrity_values
        score_columns[score_name] = composite_ready_values

        eval_type = "continuous" if predictor_type == "continuous" else predictor_type
        distribution_ok = bool(not integrity_values.dropna().empty and (predictor_type != "continuous" or integrity_values.dropna().std(ddof=0) > 0.0))
        raw_primary_spread = spread_for_predictor(raw_values, forward_0, predictor_type)
        integrity_primary_spread = spread_for_predictor(integrity_values, forward_0, eval_type)
        integrity_delay_1_spread = spread_for_predictor(integrity_values, forward_1, eval_type)
        integrity_delay_2_spread = spread_for_predictor(integrity_values, forward_2, eval_type)
        monotonicity = monotonicity_for_values(integrity_values, forward_0, eval_type)
        integrity_tier, integrity_flags, ratio, direction_ok, delay_ok = _integrity_gate(
            predictor_type,
            raw_primary_spread,
            integrity_primary_spread,
            integrity_delay_1_spread,
            integrity_delay_2_spread,
            monotonicity,
            distribution_ok,
            config,
        )

        composite_ready_spread = spread_for_predictor(composite_ready_values, forward_0, "continuous")
        delay_0_rank_metric = rank_metric_for_series(composite_ready_values, forward_0)
        delay_1_rank_metric = rank_metric_for_series(composite_ready_values, forward_1)
        delay_2_rank_metric = rank_metric_for_series(composite_ready_values, forward_2)

        rows.append(
            {
                **row_dict,
                "integrity_score_name": integrity_score_name,
                "score_name": score_name,
                "selected_method": selected_method,
                "composite_ready_method": "ts_percentile_rank",
                "raw_delay_0_spread": raw_primary_spread,
                "score_delay_0_spread": integrity_primary_spread,
                "score_delay_1_spread": integrity_delay_1_spread,
                "score_delay_2_spread": integrity_delay_2_spread,
                "composite_ready_delay_0_spread": composite_ready_spread,
                "spread_preservation_ratio": ratio,
                "monotonicity_ratio": monotonicity,
                "direction_alignment_ok": direction_ok,
                "delay_alignment_ok": delay_ok,
                "distribution_ok": distribution_ok,
                "integrity_tier": integrity_tier,
                "integrity_failure_flags": "|".join(integrity_flags),
                "delay_0_rank_metric": delay_0_rank_metric,
                "delay_1_rank_metric": delay_1_rank_metric,
                "delay_2_rank_metric": delay_2_rank_metric,
            }
        )

    score_frame = pd.concat([raw_frame, pd.DataFrame(score_columns, index=raw_frame.index)], axis=1)
    summary = pd.DataFrame(rows)
    if summary.empty:
        raise ValueError("No generated raw predictors available for score admission.")

    line_best = summary.groupby("generator_line")["delay_0_rank_metric"].max().rename("line_best_rank_metric")
    family_best = summary.groupby(["generator_line", "family"])["delay_0_rank_metric"].max().rename("family_best_rank_metric")
    summary = summary.merge(line_best, on="generator_line", how="left")
    summary = summary.merge(family_best, on=["generator_line", "family"], how="left")
    summary["generator_line_rank_strength_ratio"] = np.where(
        summary["line_best_rank_metric"] > 0.0,
        summary["delay_0_rank_metric"] / summary["line_best_rank_metric"],
        0.0,
    )
    summary["family_rank_strength_ratio"] = np.where(
        summary["family_best_rank_metric"] > 0.0,
        summary["delay_0_rank_metric"] / summary["family_best_rank_metric"],
        0.0,
    )
    summary = summary.sort_values(["generator_line", "family", "delay_0_rank_metric"], ascending=[True, True, False]).reset_index(drop=True)
    summary["family_rank"] = summary.groupby(["generator_line", "family"])["delay_0_rank_metric"].rank(method="first", ascending=False).astype(int)
    admit_mask = (
        (summary["integrity_tier"] != "fail")
        & (summary["delay_0_rank_metric"] > config.admission_rank_metric_positive)
        & (summary["delay_1_rank_metric"] > config.admission_rank_metric_positive)
        & (summary["delay_2_rank_metric"] > config.admission_rank_metric_positive)
        & (summary["delay_0_rank_metric"] >= config.admission_rank_metric_floor)
        & (summary["family_rank"] <= config.admission_family_rank_cap)
        & (summary["generator_line_rank_strength_ratio"] >= config.admission_generator_strength_floor)
        & (summary["family_rank_strength_ratio"] >= config.admission_family_strength_floor)
    )
    summary["admission_tier"] = np.where(
        admit_mask
        & (summary["generator_line_rank_strength_ratio"] >= 0.6)
        & (summary["family_rank_strength_ratio"] >= 0.75),
        "strong",
        np.where(admit_mask, "conditional", "fail"),
    )
    summary["retain_for_composite_v3"] = summary["admission_tier"] != "fail"
    summary["retain_for_composite_v2"] = summary["retain_for_composite_v3"]
    summary = summary.sort_values(["generator_line", "family", "delay_0_rank_metric"], ascending=[True, True, False]).reset_index(drop=True)

    raw_catalog.to_csv(target / "generated_raw_predictor_catalog.csv", index=False)
    summary.to_csv(target / "standardized_score_summary.csv", index=False)
    score_frame.reset_index().to_parquet(target / "standardized_score_panel.parquet", index=False)
    return {"score_frame": score_frame, "score_summary": summary}
