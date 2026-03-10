from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app_config import StandardizedScoreConfig, TSUniverseConfig
from models import AlignedPanel
from research.continuous_score_methods import apply_continuous_method
from research.raw_predictors import (
    RawPredictorSpec,
    _build_predictor_frame,
    _catalog,
    _eligible_symbols,
    _forward_return,
    _spread_for_predictor,
)


@dataclass(frozen=True, slots=True)
class StandardizedScoreSpec:
    name: str
    family: str
    predictor_type: str
    score_type: str
    source_predictor: str
    score_method: str
    direction_applied: str
    gate_type: str


def _continuous_direction_multiplier(spec: RawPredictorSpec) -> float:
    if spec.name in {"prev_day_return", "amihud_20w"}:
        return -1.0
    return 1.0


def _safe_skew(values: pd.Series) -> float:
    clean = values.dropna()
    if len(clean) < 3:
        return 0.0
    return float(clean.skew())


def _monotonicity_for_values(values: pd.Series, forward_returns: pd.Series, predictor_type: str) -> float:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna()
    if aligned.empty:
        return 0.0
    if predictor_type == "continuous_score":
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


def _spread_predictor_type(score_type: str) -> str:
    if score_type == "continuous_score":
        return "continuous"
    if score_type == "binary_score":
        return "binary_rule"
    return "ternary_rule"


def _continuous_method_for_spec(spec: RawPredictorSpec) -> str:
    if spec.name == "prev_day_return":
        return "ts_percentile_rank"
    if spec.name == "amihud_20w":
        return "ewm_zscore"
    if spec.name in {"relative_basis", "log_basis"}:
        return "level_preserve_clip_scale"
    return "ewm_zscore"


def _rule_score_builder(frame: pd.DataFrame, spec: RawPredictorSpec) -> pd.Series:
    if spec.predictor_type == "binary_rule":
        return frame[spec.name].map({1.0: 1.0, 0.0: -1.0})
    return frame[spec.name]


def _continuous_score_builder(frame: pd.DataFrame, spec: RawPredictorSpec, config: StandardizedScoreConfig) -> pd.Series:
    method = _continuous_method_for_spec(spec)
    direction = _continuous_direction_multiplier(spec)
    return frame.groupby("symbol", group_keys=False)[spec.name].transform(
        lambda values: apply_continuous_method(
            values * direction,
            method,
            window=config.z_window,
            min_periods=config.z_min_periods,
            clip_quantile=config.clip_quantile,
            ewm_span=config.ewm_span,
        )
    )


def _build_score_specs(raw_specs: list[RawPredictorSpec]) -> list[StandardizedScoreSpec]:
    specs: list[StandardizedScoreSpec] = []
    for spec in raw_specs:
        if spec.predictor_type == "continuous":
            specs.append(
                StandardizedScoreSpec(
                    name=f"{spec.name}_score",
                    family=spec.family,
                    predictor_type=spec.predictor_type,
                    score_type="continuous_score",
                    source_predictor=spec.name,
                    score_method=_continuous_method_for_spec(spec),
                    direction_applied="negate" if _continuous_direction_multiplier(spec) < 0 else "preserve",
                    gate_type="continuous_joint",
                )
            )
            continue
        if spec.predictor_type == "binary_rule":
            specs.append(
                StandardizedScoreSpec(
                    name=f"{spec.name}_score",
                    family=spec.family,
                    predictor_type=spec.predictor_type,
                    score_type="binary_score",
                    source_predictor=spec.name,
                    score_method="binary_rule_signed_mapping",
                    direction_applied="map_0_to_-1_1_to_+1",
                    gate_type="rule_based_strict",
                )
            )
            continue
        specs.append(
            StandardizedScoreSpec(
                name=f"{spec.name}_score",
                family=spec.family,
                predictor_type=spec.predictor_type,
                score_type="ternary_score",
                source_predictor=spec.name,
                score_method="ternary_rule_identity",
                direction_applied="preserve",
                gate_type="rule_based_strict",
            )
        )
    return specs


def _build_standardized_score_frame(
    predictor_frame: pd.DataFrame,
    raw_specs: list[RawPredictorSpec],
    config: StandardizedScoreConfig,
) -> pd.DataFrame:
    frame = predictor_frame.copy()
    for spec in raw_specs:
        score_name = f"{spec.name}_score"
        if spec.predictor_type == "continuous":
            frame[score_name] = _continuous_score_builder(frame, spec, config)
        else:
            frame[score_name] = _rule_score_builder(frame, spec)
    return frame


def _score_catalog_frame(score_specs: list[StandardizedScoreSpec], config: StandardizedScoreConfig) -> pd.DataFrame:
    rows = []
    for spec in score_specs:
        rows.append(
            {
                "name": spec.name,
                "family": spec.family,
                "predictor_type": spec.predictor_type,
                "score_type": spec.score_type,
                "source_predictor": spec.source_predictor,
                "score_method": spec.score_method,
                "direction_applied": spec.direction_applied,
                "gate_type": spec.gate_type,
                "z_window": config.z_window if spec.score_type == "continuous_score" else np.nan,
                "z_min_periods": config.z_min_periods if spec.score_type == "continuous_score" else np.nan,
                "clip_quantile": config.clip_quantile if spec.score_type == "continuous_score" else np.nan,
                "ewm_span": config.ewm_span if spec.score_method == "ewm_zscore" else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["family", "name"]).reset_index(drop=True)


def _score_gate_evaluator(
    score_spec: StandardizedScoreSpec,
    *,
    primary_spread: float,
    raw_primary_spread: float,
    delay_1_spread: float,
    delay_2_spread: float,
    monotonicity: float,
    distribution_ok: bool,
    config: StandardizedScoreConfig,
) -> tuple[str, bool, list[str], float, bool, bool]:
    ratio = 0.0 if raw_primary_spread == 0.0 else abs(primary_spread) / abs(raw_primary_spread)
    direction_ok = (raw_primary_spread == 0.0 and primary_spread == 0.0) or (np.sign(primary_spread) == np.sign(raw_primary_spread))
    delay_ok = not ((delay_1_spread * primary_spread) < 0 or (delay_2_spread * primary_spread) < 0)

    failures: list[str] = []
    if not direction_ok:
        failures.append("direction_mismatch")
    if not delay_ok:
        failures.append("delay_sign_flip")
    if not distribution_ok:
        failures.append("distribution_invalid")

    if score_spec.gate_type == "rule_based_strict":
        if ratio < config.rule_spread_gate:
            failures.append("spread_decay_excessive")
        pass_tier = "strong" if not failures else "fail"
        return pass_tier, pass_tier != "fail", failures or ["passed"], ratio, direction_ok, delay_ok

    if ratio >= config.continuous_strong_spread_gate:
        pass_tier = "strong" if not failures else "fail"
    elif ratio >= config.continuous_conditional_spread_gate and monotonicity >= config.continuous_conditional_monotonicity_gate and not failures:
        pass_tier = "conditional"
    else:
        pass_tier = "fail"
        if ratio < config.continuous_conditional_spread_gate:
            failures.append("spread_decay_excessive")
        if monotonicity < config.continuous_conditional_monotonicity_gate:
            failures.append("monotonicity_too_low")
    return pass_tier, pass_tier != "fail", failures or ["passed"], ratio, direction_ok, delay_ok


def _decision_log(summary: pd.DataFrame) -> str:
    lines = ["# Standardized Score Decision Log", ""]
    for tier, title in (("strong", "Strong Pass"), ("conditional", "Conditional Pass"), ("fail", "Fail")):
        lines.append(f"## {title}")
        subset = summary.loc[summary["pass_tier"] == tier].sort_values("name")
        if subset.empty:
            lines.append("- none")
            lines.append("")
            continue
        for row in subset.itertuples(index=False):
            lines.append(f"- `{row.name}`")
            lines.append(f"  - method: {row.selected_method}, gate: {row.gate_type}, ratio: {row.spread_preservation_ratio:.3f}, failures: {row.failure_flags}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_standardized_score_data_4h(panel: AlignedPanel, universe_config: TSUniverseConfig, config: StandardizedScoreConfig) -> dict[str, object]:
    symbols = _eligible_symbols(panel, universe_config)
    if not symbols:
        raise ValueError("No requested symbols are available in the aligned panel.")
    if config.z_window <= 0 or config.z_min_periods <= 0 or config.ewm_span <= 0:
        raise ValueError("z_window, z_min_periods, and ewm_span must be positive.")
    if config.z_min_periods > config.z_window:
        raise ValueError("z_min_periods cannot exceed z_window.")
    if config.winsor_clip_z <= 0:
        raise ValueError("winsor_clip_z must be positive.")
    if not 0.0 < config.clip_quantile < 0.5:
        raise ValueError("clip_quantile must be between 0 and 0.5.")
    working = panel.frame.loc[panel.frame.index.get_level_values("symbol").isin(symbols)]
    missing: list[str] = []
    if working["spot_close"].notna().sum() == 0:
        missing.append("spot_prices_4h")
    if working["index_close"].notna().sum() == 0:
        missing.append("index_prices_4h")
    if working["funding_rate_8h"].notna().sum() == 0:
        missing.append("funding_rates_8h")
    if missing:
        raise ValueError(f"Missing required standardized score inputs: {missing}")
    return {
        "status": "ok",
        "symbols": symbols,
        "required_inputs": ["perp_ohlcv", "spot_prices_4h", "index_prices_4h", "funding_rates_8h"],
        "z_window": config.z_window,
        "z_min_periods": config.z_min_periods,
        "clip_quantile": config.clip_quantile,
        "ewm_span": config.ewm_span,
    }


def run_standardized_score_research_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    config: StandardizedScoreConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    validate_standardized_score_data_4h(panel, universe_config, config)
    symbols = _eligible_symbols(panel, universe_config)
    raw_specs = [spec for spec in _catalog() if spec.readiness == "implementable"]
    predictor_frame = _build_predictor_frame(panel, symbols)
    score_frame = _build_standardized_score_frame(predictor_frame, raw_specs, config).set_index(["date", "symbol"]).sort_index()
    score_specs = _build_score_specs(raw_specs)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    score_catalog = _score_catalog_frame(score_specs, config)
    distribution_rows: list[dict[str, object]] = []
    alignment_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    delay_rows: list[dict[str, object]] = []

    base_frame = score_frame.reset_index()
    forward_primary = _forward_return(base_frame, config.primary_horizon, 0)
    raw_spreads = {spec.name: _spread_for_predictor(score_frame[spec.name], forward_primary, spec.predictor_type) for spec in raw_specs}

    for score_spec in score_specs:
        raw_spec = next(spec for spec in raw_specs if spec.name == score_spec.source_predictor)
        score_values = score_frame[score_spec.name]
        clean = score_values.dropna()
        coverage = float(score_values.notna().mean()) if len(score_values) else 0.0
        non_zero_rate = float((score_values.fillna(0.0) != 0.0).mean()) if len(score_values) else 0.0
        distribution_ok = True
        if score_spec.score_type == "continuous_score":
            distribution_ok = bool(not clean.empty and clean.std(ddof=0) > 0)
        distribution_rows.append(
            {
                "name": score_spec.name,
                "source_predictor": score_spec.source_predictor,
                "score_type": score_spec.score_type,
                "selected_method": score_spec.score_method,
                "gate_type": score_spec.gate_type,
                "coverage_ratio": coverage,
                "mean": float(clean.mean()) if not clean.empty else 0.0,
                "std": float(clean.std(ddof=0)) if not clean.empty else 0.0,
                "min": float(clean.min()) if not clean.empty else 0.0,
                "max": float(clean.max()) if not clean.empty else 0.0,
                "skew": _safe_skew(clean),
                "non_zero_rate": non_zero_rate,
                "positive_rate": float((score_values > 0).mean()) if len(score_values) else 0.0,
                "negative_rate": float((score_values < 0).mean()) if len(score_values) else 0.0,
            }
        )

        raw_series = score_frame[score_spec.source_predictor]
        aligned_pair = pd.concat([raw_series.rename("raw"), score_values.rename("score")], axis=1).dropna()
        raw_score_corr = 0.0
        if not aligned_pair.empty and aligned_pair["raw"].nunique() >= 2 and aligned_pair["score"].nunique() >= 2:
            raw_score_corr = float(aligned_pair["raw"].corr(aligned_pair["score"]))

        spread_type = _spread_predictor_type(score_spec.score_type)
        primary_spread = _spread_for_predictor(score_values, forward_primary, spread_type)
        delay_1_spread = _spread_for_predictor(score_values, _forward_return(base_frame, config.primary_horizon, 1), spread_type)
        delay_2_spread = _spread_for_predictor(score_values, _forward_return(base_frame, config.primary_horizon, 2), spread_type)
        monotonicity = _monotonicity_for_values(score_values, forward_primary, score_spec.score_type)
        raw_primary_spread = raw_spreads[score_spec.source_predictor]

        pass_tier, retain, failure_flags, ratio, direction_ok, delay_ok = _score_gate_evaluator(
            score_spec,
            primary_spread=primary_spread,
            raw_primary_spread=raw_primary_spread,
            delay_1_spread=delay_1_spread,
            delay_2_spread=delay_2_spread,
            monotonicity=monotonicity,
            distribution_ok=distribution_ok,
            config=config,
        )

        alignment_rows.append(
            {
                "name": score_spec.name,
                "source_predictor": score_spec.source_predictor,
                "raw_predictor_type": raw_spec.predictor_type,
                "score_type": score_spec.score_type,
                "selected_method": score_spec.score_method,
                "gate_type": score_spec.gate_type,
                "raw_score_correlation": raw_score_corr,
                "raw_primary_spread": raw_primary_spread,
                "score_primary_spread": primary_spread,
                "spread_preservation_ratio": ratio,
                "direction_alignment_ok": direction_ok,
                "delay_alignment_ok": delay_ok,
                "monotonicity_ratio": monotonicity,
                "retain_for_composite_v1": retain,
                "pass_tier": pass_tier,
                "failure_flags": "|".join(failure_flags),
            }
        )
        summary_rows.append(
            {
                "name": score_spec.name,
                "source_predictor": score_spec.source_predictor,
                "family": score_spec.family,
                "score_type": score_spec.score_type,
                "selected_method": score_spec.score_method,
                "gate_type": score_spec.gate_type,
                "coverage_ratio": coverage,
                "primary_horizon": config.primary_horizon,
                "delay_0_spread": primary_spread,
                "delay_1_spread": delay_1_spread,
                "delay_2_spread": delay_2_spread,
                "raw_primary_spread": raw_primary_spread,
                "spread_preservation_ratio": ratio,
                "monotonicity_ratio": monotonicity,
                "direction_alignment_ok": direction_ok,
                "distribution_ok": distribution_ok,
                "retain_for_composite_v1": retain,
                "pass_tier": pass_tier,
                "failure_flags": "|".join(failure_flags),
            }
        )
        for delay, spread in ((0, primary_spread), (1, delay_1_spread), (2, delay_2_spread)):
            delay_rows.append(
                {
                    "name": score_spec.name,
                    "source_predictor": score_spec.source_predictor,
                    "selected_method": score_spec.score_method,
                    "delay": delay,
                    "spread": spread,
                }
            )

    score_columns = [spec.name for spec in score_specs]
    score_frame.reset_index()[["date", "symbol", *score_columns]].to_parquet(target / "standardized_score_panel.parquet", index=False)

    summary = pd.DataFrame(summary_rows).sort_values(["family", "name"]).reset_index(drop=True)
    alignment = pd.DataFrame(alignment_rows).sort_values(["source_predictor", "name"]).reset_index(drop=True)
    distributions = pd.DataFrame(distribution_rows).sort_values(["source_predictor", "name"]).reset_index(drop=True)
    delay_decay = pd.DataFrame(delay_rows).sort_values(["name", "delay"]).reset_index(drop=True)

    score_catalog.to_csv(target / "standardized_score_catalog.csv", index=False)
    summary.to_csv(target / "standardized_score_summary.csv", index=False)
    delay_decay.to_csv(target / "standardized_score_delay_decay.csv", index=False)
    distributions.to_csv(target / "standardized_score_distribution.csv", index=False)
    alignment.to_csv(target / "standardized_score_alignment.csv", index=False)
    (target / "standardized_score_decision_log.md").write_text(_decision_log(summary), encoding="utf-8")

    retained = summary.loc[summary["retain_for_composite_v1"] == True, "name"].tolist()
    strong = summary.loc[summary["pass_tier"] == "strong", "name"].tolist()
    conditional = summary.loc[summary["pass_tier"] == "conditional", "name"].tolist()
    rejected = summary.loc[summary["pass_tier"] == "fail", "name"].tolist()
    return {
        "state": "complete",
        "retained_scores": retained,
        "strong_scores": strong,
        "conditional_scores": conditional,
        "rejected_scores": rejected,
        "artifacts": {
            "catalog": "standardized_score_catalog.csv",
            "panel": "standardized_score_panel.parquet",
            "summary": "standardized_score_summary.csv",
            "delay_decay": "standardized_score_delay_decay.csv",
            "distribution": "standardized_score_distribution.csv",
            "alignment": "standardized_score_alignment.csv",
            "decision_log": "standardized_score_decision_log.md",
        },
    }
