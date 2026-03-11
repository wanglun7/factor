from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleFamilySpec:
    id: str
    predictor_type: str
    alpha_direction_policy: str
    required_columns: tuple[str, ...]


def build_rule_family_registry() -> dict[str, RuleFamilySpec]:
    return {
        "moving_average_rule": RuleFamilySpec(
            id="moving_average_rule",
            predictor_type="binary_rule",
            alpha_direction_policy="preserve",
            required_columns=("close",),
        ),
        "trading_range_breakout": RuleFamilySpec(
            id="trading_range_breakout",
            predictor_type="ternary_rule",
            alpha_direction_policy="preserve",
            required_columns=("close",),
        ),
        "filter_rule": RuleFamilySpec(
            id="filter_rule",
            predictor_type="ternary_rule",
            alpha_direction_policy="preserve",
            required_columns=("close",),
        ),
    }
