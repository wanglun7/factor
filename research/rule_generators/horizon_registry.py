from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleHorizonSpec:
    id: str
    horizon_group: str
    native_window: int
    mapped_window_4h: int
    mapping_method: str


def build_rule_horizon_registry() -> dict[str, RuleHorizonSpec]:
    return {
        "native_12": RuleHorizonSpec("native_12", "native_intraday", 12, 12, "native_intraday"),
        "native_24": RuleHorizonSpec("native_24", "native_intraday", 24, 24, "native_intraday"),
        "native_72": RuleHorizonSpec("native_72", "native_intraday", 72, 72, "native_intraday"),
        "daily_20": RuleHorizonSpec("daily_20", "classic_daily", 20, 120, "calendar_equivalent"),
        "daily_50": RuleHorizonSpec("daily_50", "classic_daily", 50, 300, "calendar_equivalent"),
        "daily_60": RuleHorizonSpec("daily_60", "classic_daily", 60, 360, "calendar_equivalent"),
        "daily_150": RuleHorizonSpec("daily_150", "classic_daily", 150, 900, "calendar_equivalent"),
        "daily_200": RuleHorizonSpec("daily_200", "classic_daily", 200, 1200, "calendar_equivalent"),
    }
