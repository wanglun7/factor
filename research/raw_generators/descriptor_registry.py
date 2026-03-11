from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DescriptorSpec:
    id: str
    family: str
    predictor_type: str
    alpha_direction_policy: str
    score_method_family: str
    required_columns: tuple[str, ...]
    horizon_ids: tuple[str, ...]
    transform_ids: tuple[str, ...]


def build_descriptor_registry() -> dict[str, DescriptorSpec]:
    return {
        "return": DescriptorSpec(
            id="return",
            family="return_based",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="return_based",
            required_columns=("ret_1bar", "ret_6bar", "ret_18bar", "ret_30bar", "ret_120bar", "realized_vol_120bar"),
            horizon_ids=("bar_1", "bar_6", "bar_18", "bar_30", "bar_120"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile", "vol_adjusted"),
        ),
        "realized_volatility": DescriptorSpec(
            id="realized_volatility",
            family="volatility_liquidity",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="volatility_liquidity",
            required_columns=("realized_vol_30bar", "realized_vol_120bar"),
            horizon_ids=("bar_30", "bar_120"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile"),
        ),
        "dollar_volume": DescriptorSpec(
            id="dollar_volume",
            family="volatility_liquidity",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="volatility_liquidity",
            required_columns=("avg_dollar_volume_30bar", "avg_dollar_volume_120bar"),
            horizon_ids=("bar_30", "bar_120"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile"),
        ),
        "amihud": DescriptorSpec(
            id="amihud",
            family="volatility_liquidity",
            predictor_type="continuous",
            alpha_direction_policy="negate",
            score_method_family="volatility_liquidity",
            required_columns=("amihud_30bar", "amihud_120bar"),
            horizon_ids=("bar_30", "bar_120"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile"),
        ),
        "funding": DescriptorSpec(
            id="funding",
            family="derivatives_carry_funding",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="derivatives_carry_funding",
            required_columns=("funding_rate_lag1",),
            horizon_ids=("period_1", "period_21", "period_90"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile"),
        ),
        "basis": DescriptorSpec(
            id="basis",
            family="derivatives_carry_funding",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="basis_like",
            required_columns=("close", "spot_close", "realized_vol_120bar"),
            horizon_ids=("bar_1", "bar_30"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile", "vol_adjusted"),
        ),
        "premium": DescriptorSpec(
            id="premium",
            family="derivatives_carry_funding",
            predictor_type="continuous",
            alpha_direction_policy="preserve",
            score_method_family="derivatives_carry_funding",
            required_columns=("close", "index_close", "realized_vol_120bar"),
            horizon_ids=("bar_1", "bar_30"),
            transform_ids=("level", "change", "deviation", "ratio", "percentile", "vol_adjusted"),
        ),
    }
