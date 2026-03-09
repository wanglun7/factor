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


@dataclass(frozen=True, slots=True)
class UniverseConfig:
    selection_size: int
    min_listing_days: int
    min_avg_dollar_volume: float


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    momentum_lookback: int
    reversal_lookback: int
    momentum_weight: float
    reversal_weight: float


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    long_n: int
    short_n: int
    gross_exposure: float
    net_exposure: float
    max_abs_weight: float
    turnover_limit: float
    rebalance_frequency: str


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    one_way_cost_bps: float
    benchmark_symbol: str
    output_dir: str


@dataclass(frozen=True, slots=True)
class RunConfig:
    data: DataConfig
    universe: UniverseConfig
    strategy: StrategyConfig
    portfolio: PortfolioConfig
    backtest: BacktestConfig


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(path: str | Path) -> RunConfig:
    raw = _read_yaml(path)
    data = raw.get("data", {}) or {}
    universe = raw.get("universe", {}) or {}
    strategy = raw.get("strategy", {}) or {}
    portfolio = raw.get("portfolio", {}) or {}
    backtest = raw.get("backtest", {}) or {}

    return RunConfig(
        data=DataConfig(
            provider=str(data.get("provider", "local_csv")),
            csv_dir=str(data.get("csv_dir", "local_data")),
            start_date=str(data.get("start_date", "2021-01-01")),
            end_date=str(data.get("end_date", "2024-12-31")),
        ),
        universe=UniverseConfig(
            selection_size=int(universe.get("selection_size", 30)),
            min_listing_days=int(universe.get("min_listing_days", 90)),
            min_avg_dollar_volume=float(universe.get("min_avg_dollar_volume", 0.0)),
        ),
        strategy=StrategyConfig(
            momentum_lookback=int(strategy.get("momentum_lookback", 20)),
            reversal_lookback=int(strategy.get("reversal_lookback", 3)),
            momentum_weight=float(strategy.get("momentum_weight", 1.0)),
            reversal_weight=float(strategy.get("reversal_weight", 1.0)),
        ),
        portfolio=PortfolioConfig(
            long_n=int(portfolio.get("long_n", 10)),
            short_n=int(portfolio.get("short_n", 10)),
            gross_exposure=float(portfolio.get("gross_exposure", 1.0)),
            net_exposure=float(portfolio.get("net_exposure", 0.0)),
            max_abs_weight=float(portfolio.get("max_abs_weight", 0.15)),
            turnover_limit=float(portfolio.get("turnover_limit", 0.40)),
            rebalance_frequency=str(portfolio.get("rebalance_frequency", "weekly_monday")),
        ),
        backtest=BacktestConfig(
            one_way_cost_bps=float(backtest.get("one_way_cost_bps", 10)),
            benchmark_symbol=str(backtest.get("benchmark_symbol", "BTC")),
            output_dir=str(backtest.get("output_dir", "artifacts/phase1")),
        ),
    )
