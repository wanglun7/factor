from __future__ import annotations

from dataclasses import dataclass

from app_config import RuleGeneratorConfig

from .family_registry import build_rule_family_registry
from .form_registry import build_rule_form_registry
from .horizon_registry import build_rule_horizon_registry
from .threshold_registry import build_filter_threshold_bps_registry


@dataclass(frozen=True, slots=True)
class GeneratedRuleSpec:
    name: str
    generator_line: str
    rule_family: str
    form_id: str
    predictor_type: str
    horizon_group: str
    native_window: int
    mapped_window_4h: int
    mapping_method: str
    threshold_bps: int | None
    short_window: int | None
    long_window: int | None
    required_columns: tuple[str, ...]
    alpha_direction_policy: str


def _single_window_name(form_id: str, horizon_id: str, threshold_bps: int | None = None) -> str:
    suffix = f"_th{threshold_bps}bps" if threshold_bps is not None else ""
    return f"{form_id}_{horizon_id}{suffix}"


def _pair_name(form_id: str, short_horizon_id: str, long_horizon_id: str) -> str:
    return f"{form_id}_{short_horizon_id}_{long_horizon_id}"


def build_generated_rule_specs(config: RuleGeneratorConfig) -> list[GeneratedRuleSpec]:
    family_registry = build_rule_family_registry()
    form_registry = build_rule_form_registry()
    horizon_registry = build_rule_horizon_registry()
    threshold_registry = build_filter_threshold_bps_registry()

    unknown_families = sorted(set(config.families) - set(family_registry))
    unknown_forms = sorted(set(config.forms) - set(form_registry))
    unknown_groups = sorted(set(config.horizon_groups) - {spec.horizon_group for spec in horizon_registry.values()})
    unknown_thresholds = sorted(set(config.filter_threshold_bps) - set(threshold_registry))
    if unknown_families:
        raise ValueError(f"Unknown rule generator families: {unknown_families}")
    if unknown_forms:
        raise ValueError(f"Unknown rule generator forms: {unknown_forms}")
    if unknown_groups:
        raise ValueError(f"Unknown rule generator horizon groups: {unknown_groups}")
    if unknown_thresholds:
        raise ValueError(f"Unknown rule generator thresholds: {unknown_thresholds}")

    specs: list[GeneratedRuleSpec] = []
    allowed_horizons = [spec for spec in horizon_registry.values() if spec.horizon_group in config.horizon_groups]

    for form_id in config.forms:
        form = form_registry[form_id]
        if form.rule_family not in config.families:
            continue
        family = family_registry[form.rule_family]
        form_horizons = [spec for spec in allowed_horizons if spec.horizon_group in config.horizon_groups]

        if form.form_kind == "single_window" and not form.requires_threshold:
            for horizon in form_horizons:
                specs.append(
                    GeneratedRuleSpec(
                        name=_single_window_name(form_id, horizon.id),
                        generator_line="rule_grammar_based",
                        rule_family=form.rule_family,
                        form_id=form.id,
                        predictor_type=family.predictor_type,
                        horizon_group=horizon.horizon_group,
                        native_window=horizon.native_window,
                        mapped_window_4h=horizon.mapped_window_4h,
                        mapping_method=horizon.mapping_method,
                        threshold_bps=None,
                        short_window=None,
                        long_window=None,
                        required_columns=family.required_columns,
                        alpha_direction_policy=family.alpha_direction_policy,
                    )
                )
            continue

        if form.form_kind == "single_window" and form.requires_threshold:
            for horizon in form_horizons:
                for threshold_bps in config.filter_threshold_bps:
                    specs.append(
                        GeneratedRuleSpec(
                            name=_single_window_name(form_id, horizon.id, threshold_bps),
                            generator_line="rule_grammar_based",
                            rule_family=form.rule_family,
                            form_id=form.id,
                            predictor_type=family.predictor_type,
                            horizon_group=horizon.horizon_group,
                            native_window=horizon.native_window,
                            mapped_window_4h=horizon.mapped_window_4h,
                            mapping_method=horizon.mapping_method,
                            threshold_bps=threshold_bps,
                            short_window=None,
                            long_window=None,
                            required_columns=family.required_columns,
                            alpha_direction_policy=family.alpha_direction_policy,
                        )
                    )
            continue

        if form.form_kind == "window_pair":
            for group in config.horizon_groups:
                group_horizons = [spec for spec in form_horizons if spec.horizon_group == group]
                for i, short_horizon in enumerate(group_horizons):
                    for long_horizon in group_horizons[i + 1 :]:
                        specs.append(
                            GeneratedRuleSpec(
                                name=_pair_name(form_id, short_horizon.id, long_horizon.id),
                                generator_line="rule_grammar_based",
                                rule_family=form.rule_family,
                                form_id=form.id,
                                predictor_type=family.predictor_type,
                                horizon_group=group,
                                native_window=long_horizon.native_window,
                                mapped_window_4h=long_horizon.mapped_window_4h,
                                mapping_method=long_horizon.mapping_method,
                                threshold_bps=None,
                                short_window=short_horizon.mapped_window_4h,
                                long_window=long_horizon.mapped_window_4h,
                                required_columns=family.required_columns,
                                alpha_direction_policy=family.alpha_direction_policy,
                            )
                        )
            continue

        raise ValueError(f"Unsupported rule form kind: {form.form_kind}")

    return specs
