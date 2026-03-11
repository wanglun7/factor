from __future__ import annotations

from dataclasses import dataclass

from app_config import RawGeneratorV2Config

from .descriptor_registry import DescriptorSpec, build_descriptor_registry
from .horizon_registry import HorizonSpec, build_horizon_registry
from .transform_registry import TransformSpec, build_transform_registry


@dataclass(frozen=True, slots=True)
class GeneratedDescriptorSpec:
    name: str
    generator_line: str
    descriptor_id: str
    descriptor_family: str
    transform_id: str
    horizon_id: str
    horizon_group: str
    horizon_window: int
    horizon_unit: str
    predictor_type: str
    alpha_direction_policy: str
    score_method_family: str
    required_columns: tuple[str, ...]


def _is_valid_combo(descriptor: DescriptorSpec, transform: TransformSpec, horizon: HorizonSpec) -> bool:
    if transform.id not in descriptor.transform_ids:
        return False
    if horizon.id not in descriptor.horizon_ids:
        return False
    if horizon.window < transform.min_window:
        return False
    if transform.id == "vol_adjusted" and descriptor.id not in {"return", "basis", "premium"}:
        return False
    return True


def _predictor_name(descriptor: DescriptorSpec, transform: TransformSpec, horizon: HorizonSpec) -> str:
    return f"{descriptor.id}_{transform.id}_{horizon.id}"


def build_generated_specs(config: RawGeneratorV2Config) -> list[GeneratedDescriptorSpec]:
    descriptor_registry = build_descriptor_registry()
    transform_registry = build_transform_registry()
    horizon_registry = build_horizon_registry()

    unknown_descriptors = sorted(set(config.descriptors) - set(descriptor_registry))
    unknown_transforms = sorted(set(config.transforms) - set(transform_registry))
    unknown_groups = sorted(set(config.horizon_groups) - {spec.group for spec in horizon_registry.values()})
    if unknown_descriptors:
        raise ValueError(f"Unknown raw generator descriptors: {unknown_descriptors}")
    if unknown_transforms:
        raise ValueError(f"Unknown raw generator transforms: {unknown_transforms}")
    if unknown_groups:
        raise ValueError(f"Unknown raw generator horizon groups: {unknown_groups}")

    specs: list[GeneratedDescriptorSpec] = []
    for descriptor_id in config.descriptors:
        descriptor = descriptor_registry[descriptor_id]
        for horizon_id in descriptor.horizon_ids:
            horizon = horizon_registry[horizon_id]
            if horizon.group not in config.horizon_groups:
                continue
            for transform_id in descriptor.transform_ids:
                if transform_id not in config.transforms:
                    continue
                transform = transform_registry[transform_id]
                if not _is_valid_combo(descriptor, transform, horizon):
                    continue
                specs.append(
                    GeneratedDescriptorSpec(
                        name=_predictor_name(descriptor, transform, horizon),
                        generator_line="descriptor_based",
                        descriptor_id=descriptor.id,
                        descriptor_family=descriptor.family,
                        transform_id=transform.id,
                        horizon_id=horizon.id,
                        horizon_group=horizon.group,
                        horizon_window=horizon.window,
                        horizon_unit=horizon.unit,
                        predictor_type=descriptor.predictor_type,
                        alpha_direction_policy=descriptor.alpha_direction_policy,
                        score_method_family=descriptor.score_method_family,
                        required_columns=descriptor.required_columns,
                    )
                )
    return specs
