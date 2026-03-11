from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransformSpec:
    id: str
    family: str
    min_window: int


def build_transform_registry() -> dict[str, TransformSpec]:
    return {
        "level": TransformSpec(id="level", family="simple", min_window=1),
        "change": TransformSpec(id="change", family="simple", min_window=1),
        "deviation": TransformSpec(id="deviation", family="simple", min_window=2),
        "ratio": TransformSpec(id="ratio", family="simple", min_window=2),
        "percentile": TransformSpec(id="percentile", family="simple", min_window=5),
        "vol_adjusted": TransformSpec(id="vol_adjusted", family="simple", min_window=1),
    }
