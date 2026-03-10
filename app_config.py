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
class RawPredictorConfig:
    output_dir: str
    horizons: list[int]
    primary_horizon: int
    bars_per_day: int
    annualization: int


@dataclass(frozen=True, slots=True)
class StandardizedScoreConfig:
    output_dir: str
    horizons: list[int]
    primary_horizon: int
    z_window: int
    z_min_periods: int
    winsor_clip_z: float
    clip_quantile: float
    ewm_span: int
    rule_spread_gate: float
    continuous_strong_spread_gate: float
    continuous_conditional_spread_gate: float
    continuous_conditional_monotonicity_gate: float


@dataclass(frozen=True, slots=True)
class ContinuousScoreExperimentConfig:
    output_dir: str
    horizons: list[int]
    primary_horizon: int
    window: int
    min_periods: int
    clip_quantile: float
    ewm_span: int


@dataclass(frozen=True, slots=True)
class TSBacktestConfig:
    benchmark_symbol: str
    output_dir: str
    risk_weight_vol_window: int


@dataclass(frozen=True, slots=True)
class RunConfig:
    data: DataConfig
    ts_universe: TSUniverseConfig
    ts_research: TSResearchConfig
    ts_backtest: TSBacktestConfig
    raw_predictors: RawPredictorConfig
    standardized_scores: StandardizedScoreConfig
    continuous_score_experiment: ContinuousScoreExperimentConfig


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(path: str | Path) -> RunConfig:
    raw = _read_yaml(path)
    data = raw.get("data", {}) or {}
    ts_universe = raw.get("ts_universe", {}) or {}
    ts_research = raw.get("ts_research", {}) or {}
    ts_backtest = raw.get("ts_backtest", {}) or {}
    raw_predictors = raw.get("raw_predictors", {}) or {}
    standardized_scores = raw.get("standardized_scores", {}) or {}
    continuous_score_experiment = raw.get("continuous_score_experiment", {}) or {}

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
        raw_predictors=RawPredictorConfig(
            output_dir=str(raw_predictors.get("output_dir", "artifacts/raw_predictors_4h")),
            horizons=[int(x) for x in raw_predictors.get("horizons", ts_research.get("horizons", [6, 18, 30, 60, 120]))],
            primary_horizon=int(raw_predictors.get("primary_horizon", ts_research.get("primary_horizon", 30))),
            bars_per_day=int(raw_predictors.get("bars_per_day", default_bars_per_day)),
            annualization=int(raw_predictors.get("annualization", default_annualization)),
        ),
        standardized_scores=StandardizedScoreConfig(
            output_dir=str(standardized_scores.get("output_dir", "artifacts/standardized_scores_4h")),
            horizons=[int(x) for x in standardized_scores.get("horizons", ts_research.get("horizons", [6, 18, 30, 60, 120]))],
            primary_horizon=int(standardized_scores.get("primary_horizon", ts_research.get("primary_horizon", 30))),
            z_window=int(standardized_scores.get("z_window", 1512)),
            z_min_periods=int(standardized_scores.get("z_min_periods", 360)),
            winsor_clip_z=float(standardized_scores.get("winsor_clip_z", 3.0)),
            clip_quantile=float(standardized_scores.get("clip_quantile", 0.01)),
            ewm_span=int(standardized_scores.get("ewm_span", 1512)),
            rule_spread_gate=float(standardized_scores.get("rule_spread_gate", 0.7)),
            continuous_strong_spread_gate=float(standardized_scores.get("continuous_strong_spread_gate", 0.7)),
            continuous_conditional_spread_gate=float(standardized_scores.get("continuous_conditional_spread_gate", 0.45)),
            continuous_conditional_monotonicity_gate=float(standardized_scores.get("continuous_conditional_monotonicity_gate", 0.5)),
        ),
        continuous_score_experiment=ContinuousScoreExperimentConfig(
            output_dir=str(continuous_score_experiment.get("output_dir", "artifacts/continuous_score_experiment_4h")),
            horizons=[int(x) for x in continuous_score_experiment.get("horizons", ts_research.get("horizons", [6, 18, 30, 60, 120]))],
            primary_horizon=int(continuous_score_experiment.get("primary_horizon", ts_research.get("primary_horizon", 30))),
            window=int(continuous_score_experiment.get("window", 1512)),
            min_periods=int(continuous_score_experiment.get("min_periods", 360)),
            clip_quantile=float(continuous_score_experiment.get("clip_quantile", 0.01)),
            ewm_span=int(continuous_score_experiment.get("ewm_span", 1512)),
        ),
    )
