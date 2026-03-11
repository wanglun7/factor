from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class DataConfig:
    provider: str
    csv_dir: str
    start_date: str
    end_date: str
    bar_interval: str
    price_basis: str
    price_file: str
    spot_price_file: str
    index_price_file: str
    funding_file: str
    open_interest_file: str


@dataclass(frozen=True, slots=True)
class TSUniverseConfig:
    symbols: list[str]


@dataclass(frozen=True, slots=True)
class TSResearchConfig:
    horizons: list[int]
    primary_horizon: int
    signal_z_window: int
    signal_z_min_periods: int
    entry_z: float
    exit_z: float
    one_way_cost_bps: float
    output_dir: str
    min_history_bars: int
    annualization: int
    bars_per_day: int


@dataclass(frozen=True, slots=True)
class TSBacktestConfig:
    benchmark_symbol: str
    output_dir: str
    risk_weight_vol_window: int


@dataclass(frozen=True, slots=True)
class RawGeneratorV2Config:
    output_dir: str
    symbols: list[str]
    descriptors: list[str]
    transforms: list[str]
    horizon_groups: list[str]
    primary_horizon: int


@dataclass(frozen=True, slots=True)
class RuleGeneratorConfig:
    output_dir: str
    symbols: list[str]
    families: list[str]
    forms: list[str]
    horizon_groups: list[str]
    filter_threshold_bps: list[int]
    primary_horizon: int


@dataclass(frozen=True, slots=True)
class RawGenerationConfig:
    descriptor: RawGeneratorV2Config
    rule: RuleGeneratorConfig


@dataclass(frozen=True, slots=True)
class ScoreAdmissionConfig:
    output_dir: str
    horizons: list[int]
    primary_horizon: int
    z_window: int
    z_min_periods: int
    clip_quantile: float
    ewm_span: int
    rule_integrity_spread_gate: float
    continuous_strong_spread_gate: float
    continuous_conditional_spread_gate: float
    continuous_conditional_monotonicity_gate: float
    admission_generator_strength_floor: float
    admission_family_strength_floor: float
    admission_family_rank_cap: int
    admission_rank_metric_positive: float
    admission_rank_metric_floor: float


@dataclass(frozen=True, slots=True)
class CompositeExperimentConfig:
    output_dir: str
    horizons: list[int]
    primary_horizon: int
    max_scores_per_family: int
    redundancy_corr_threshold: float
    anchor_satellite_weights: list[float]
    robust_relative_strength_floor: float
    robust_stability_improvement_min: float
    bootstrap_block_size: int
    bootstrap_samples: int
    bootstrap_seed: int
    ic_weighted_subcomposite: bool


@dataclass(frozen=True, slots=True)
class ScaledAlphaConfig:
    output_dir: str
    primary_horizon: int
    calibration_window: str
    bucket_count: int
    min_train_points: int
    scale_quantile: float
    clip_min: float
    clip_max: float


@dataclass(frozen=True, slots=True)
class RunConfig:
    data: DataConfig
    ts_universe: TSUniverseConfig
    ts_research: TSResearchConfig
    ts_backtest: TSBacktestConfig
    raw_generation: RawGenerationConfig
    score_admission: ScoreAdmissionConfig
    composite_experiment: CompositeExperimentConfig
    scaled_alpha: ScaledAlphaConfig


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(path: str | Path) -> RunConfig:
    raw = _read_yaml(path)
    data = raw.get("data", {}) or {}
    ts_universe = raw.get("ts_universe", {}) or {}
    ts_research = raw.get("ts_research", {}) or {}
    ts_backtest = raw.get("ts_backtest", {}) or {}
    raw_generation = raw.get("raw_generation", {}) or {}
    descriptor = raw_generation.get("descriptor", raw.get("raw_generator_v2", {}) or {}) or {}
    rule = raw_generation.get("rule", raw.get("rule_generator", {}) or {}) or {}
    score_admission = raw.get("score_admission", raw.get("standardized_scores", {}) or {}) or {}
    composite_experiment = raw.get("composite_experiment", raw.get("composite_alpha", {}) or {}) or {}
    scaled_alpha = raw.get("scaled_alpha", {}) or {}

    default_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "ATOM"]
    default_bars_per_day = int(ts_research.get("bars_per_day", 6))
    default_annualization = int(ts_research.get("annualization", default_bars_per_day * 365))

    return RunConfig(
        data=DataConfig(
            provider=str(data.get("provider", "local_csv")),
            csv_dir=str(data.get("csv_dir", "local_data")),
            start_date=str(data.get("start_date", "2021-01-01")),
            end_date=str(data.get("end_date", "2024-12-31")),
            bar_interval=str(data.get("bar_interval", "4h")),
            price_basis=str(data.get("price_basis", "binance_perp")),
            price_file=str(data.get("price_file", "prices_4h_perp.csv")),
            spot_price_file=str(data.get("spot_price_file", "spot_prices_4h.csv")),
            index_price_file=str(data.get("index_price_file", "index_prices_4h.csv")),
            funding_file=str(data.get("funding_file", "funding_rates_8h.csv")),
            open_interest_file=str(data.get("open_interest_file", "open_interest_8h.csv")),
        ),
        ts_universe=TSUniverseConfig(
            symbols=[str(symbol) for symbol in ts_universe.get("symbols", default_symbols)],
        ),
        ts_research=TSResearchConfig(
            horizons=[int(x) for x in ts_research.get("horizons", [6, 18, 30, 60, 120])],
            primary_horizon=int(ts_research.get("primary_horizon", 30)),
            signal_z_window=int(ts_research.get("signal_z_window", 1512)),
            signal_z_min_periods=int(ts_research.get("signal_z_min_periods", 360)),
            entry_z=float(ts_research.get("entry_z", 0.75)),
            exit_z=float(ts_research.get("exit_z", 0.25)),
            one_way_cost_bps=float(ts_research.get("one_way_cost_bps", 10)),
            output_dir=str(ts_research.get("output_dir", "artifacts/ts4h_factor_research")),
            min_history_bars=int(ts_research.get("min_history_bars", 540)),
            annualization=default_annualization,
            bars_per_day=default_bars_per_day,
        ),
        ts_backtest=TSBacktestConfig(
            benchmark_symbol=str(ts_backtest.get("benchmark_symbol", "BTC")),
            output_dir=str(ts_backtest.get("output_dir", "artifacts/ts4h_walkforward")),
            risk_weight_vol_window=int(ts_backtest.get("risk_weight_vol_window", 120)),
        ),
        raw_generation=RawGenerationConfig(
            descriptor=RawGeneratorV2Config(
                output_dir=str(descriptor.get("output_dir", "artifacts/raw_generation/descriptor")),
                symbols=[str(symbol) for symbol in descriptor.get("symbols", ["BTC"])],
                descriptors=[str(item) for item in descriptor.get("descriptors", ["return", "realized_volatility", "dollar_volume", "amihud", "funding", "basis", "premium"])],
                transforms=[str(item) for item in descriptor.get("transforms", ["level", "change", "deviation", "ratio", "percentile", "vol_adjusted"])],
                horizon_groups=[str(item) for item in descriptor.get("horizon_groups", ["short", "medium", "long"])],
                primary_horizon=int(descriptor.get("primary_horizon", 30)),
            ),
            rule=RuleGeneratorConfig(
                output_dir=str(rule.get("output_dir", "artifacts/raw_generation/rule")),
                symbols=[str(symbol) for symbol in rule.get("symbols", ["BTC"])],
                families=[str(item) for item in rule.get("families", ["moving_average_rule", "trading_range_breakout", "filter_rule"])],
                forms=[str(item) for item in rule.get("forms", ["price_above_sma", "price_above_ema", "sma_crossover", "ema_crossover", "breakout_high_low", "price_filter_from_lag"])],
                horizon_groups=[str(item) for item in rule.get("horizon_groups", ["native_intraday", "classic_daily"])],
                filter_threshold_bps=[int(x) for x in rule.get("filter_threshold_bps", [50, 100, 200])],
                primary_horizon=int(rule.get("primary_horizon", 30)),
            ),
        ),
        score_admission=ScoreAdmissionConfig(
            output_dir=str(score_admission.get("output_dir", "artifacts/score_admission_4h")),
            horizons=[int(x) for x in score_admission.get("horizons", ts_research.get("horizons", [6, 18, 30, 60, 120]))],
            primary_horizon=int(score_admission.get("primary_horizon", ts_research.get("primary_horizon", 30))),
            z_window=int(score_admission.get("z_window", 1512)),
            z_min_periods=int(score_admission.get("z_min_periods", 360)),
            clip_quantile=float(score_admission.get("clip_quantile", 0.01)),
            ewm_span=int(score_admission.get("ewm_span", 1512)),
            rule_integrity_spread_gate=float(score_admission.get("rule_integrity_spread_gate", 0.7)),
            continuous_strong_spread_gate=float(score_admission.get("continuous_strong_spread_gate", 0.7)),
            continuous_conditional_spread_gate=float(score_admission.get("continuous_conditional_spread_gate", 0.45)),
            continuous_conditional_monotonicity_gate=float(score_admission.get("continuous_conditional_monotonicity_gate", 0.5)),
            admission_generator_strength_floor=float(score_admission.get("admission_generator_strength_floor", score_admission.get("admission_global_strength_floor", 0.30))),
            admission_family_strength_floor=float(score_admission.get("admission_family_strength_floor", 0.50)),
            admission_family_rank_cap=int(score_admission.get("admission_family_rank_cap", 3)),
            admission_rank_metric_positive=float(score_admission.get("admission_rank_metric_positive", 0.0)),
            admission_rank_metric_floor=float(score_admission.get("admission_rank_metric_floor", 0.015)),
        ),
        composite_experiment=CompositeExperimentConfig(
            output_dir=str(composite_experiment.get("output_dir", "artifacts/composite_experiment_4h")),
            horizons=[int(x) for x in composite_experiment.get("horizons", ts_research.get("horizons", [6, 18, 30, 60, 120]))],
            primary_horizon=int(composite_experiment.get("primary_horizon", ts_research.get("primary_horizon", 30))),
            max_scores_per_family=int(composite_experiment.get("max_scores_per_family", 2)),
            redundancy_corr_threshold=float(composite_experiment.get("redundancy_corr_threshold", 0.85)),
            anchor_satellite_weights=[float(x) for x in composite_experiment.get("anchor_satellite_weights", [0.10, 0.20, 0.30])],
            robust_relative_strength_floor=float(composite_experiment.get("robust_relative_strength_floor", 0.90)),
            robust_stability_improvement_min=float(composite_experiment.get("robust_stability_improvement_min", 0.05)),
            bootstrap_block_size=int(composite_experiment.get("bootstrap_block_size", 24)),
            bootstrap_samples=int(composite_experiment.get("bootstrap_samples", 200)),
            bootstrap_seed=int(composite_experiment.get("bootstrap_seed", 7)),
            ic_weighted_subcomposite=bool(composite_experiment.get("ic_weighted_subcomposite", True)),
        ),
        scaled_alpha=ScaledAlphaConfig(
            output_dir=str(scaled_alpha.get("output_dir", "artifacts/scaled_alpha_4h")),
            primary_horizon=int(scaled_alpha.get("primary_horizon", composite_experiment.get("primary_horizon", ts_research.get("primary_horizon", 30)))),
            calibration_window=str(scaled_alpha.get("calibration_window", "expanding")),
            bucket_count=int(scaled_alpha.get("bucket_count", 5)),
            min_train_points=int(scaled_alpha.get("min_train_points", 252)),
            scale_quantile=float(scaled_alpha.get("scale_quantile", 0.95)),
            clip_min=float(scaled_alpha.get("clip_min", -1.0)),
            clip_max=float(scaled_alpha.get("clip_max", 1.0)),
        ),
    )
