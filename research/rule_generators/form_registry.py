from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleFormSpec:
    id: str
    rule_family: str
    form_kind: str
    requires_threshold: bool
    requires_pair: bool


def build_rule_form_registry() -> dict[str, RuleFormSpec]:
    return {
        "price_above_sma": RuleFormSpec("price_above_sma", "moving_average_rule", "single_window", False, False),
        "price_above_ema": RuleFormSpec("price_above_ema", "moving_average_rule", "single_window", False, False),
        "sma_crossover": RuleFormSpec("sma_crossover", "moving_average_rule", "window_pair", False, True),
        "ema_crossover": RuleFormSpec("ema_crossover", "moving_average_rule", "window_pair", False, True),
        "breakout_high_low": RuleFormSpec("breakout_high_low", "trading_range_breakout", "single_window", False, False),
        "price_filter_from_lag": RuleFormSpec("price_filter_from_lag", "filter_rule", "single_window", True, False),
    }
