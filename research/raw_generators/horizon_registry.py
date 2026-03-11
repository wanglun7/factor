from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HorizonSpec:
    id: str
    window: int
    group: str
    unit: str


def build_horizon_registry() -> dict[str, HorizonSpec]:
    return {
        "bar_1": HorizonSpec(id="bar_1", window=1, group="short", unit="bar"),
        "bar_6": HorizonSpec(id="bar_6", window=6, group="short", unit="bar"),
        "bar_18": HorizonSpec(id="bar_18", window=18, group="short", unit="bar"),
        "bar_30": HorizonSpec(id="bar_30", window=30, group="medium", unit="bar"),
        "bar_120": HorizonSpec(id="bar_120", window=120, group="long", unit="bar"),
        "period_1": HorizonSpec(id="period_1", window=1, group="short", unit="period"),
        "period_21": HorizonSpec(id="period_21", window=21, group="medium", unit="period"),
        "period_90": HorizonSpec(id="period_90", window=90, group="long", unit="period"),
    }
