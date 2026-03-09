from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from app_config import BacktestConfig, PortfolioConfig, UniverseConfig
from backtest.metrics import summarize_metrics
from data.universe import build_universe
from models import AlignedPanel, BacktestResult
from portfolio.constructor import construct_target_weights
from strategy.signal import MomentumReversalSignal


def _compute_rebalance_dates(dates: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    if frequency == "daily":
        return dates
    if frequency == "weekly_monday":
        mondays = dates[dates.weekday == 0]
        return mondays if len(mondays) > 0 else pd.DatetimeIndex([dates.min()])
    if frequency == "monthly":
        return pd.DatetimeIndex(pd.Series(dates, index=dates).groupby(dates.to_period("M")).min().tolist())
    raise ValueError(f"Unsupported rebalance frequency: {frequency}")


def _empty_weights(symbols: Iterable[str]) -> pd.Series:
    return pd.Series(0.0, index=sorted(symbols), dtype=float)


def _drift_weights(weights: pd.Series, asset_returns: pd.Series) -> pd.Series:
    aligned_returns = asset_returns.reindex(weights.index).fillna(0.0)
    gross_return = float((weights * aligned_returns).sum())
    if float(weights.abs().sum()) == 0.0:
        return weights.copy()
    drifted = weights * (1.0 + aligned_returns)
    denominator = 1.0 + gross_return
    if denominator <= 0.0:
        return _empty_weights(weights.index)
    return (drifted / denominator).fillna(0.0)


def _compute_forward_return(panel: AlignedPanel, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.Series:
    start_close = panel.cross_section(start_date)["close"]
    end_close = panel.cross_section(end_date)["close"]
    joined = pd.concat([start_close.rename("start_close"), end_close.rename("end_close")], axis=1).dropna()
    return (joined["end_close"] / joined["start_close"] - 1.0).rename("forward_return")


def _compute_top_bottom_spread(signal: pd.Series, forward_return: pd.Series) -> float:
    aligned = pd.concat([signal.rename("signal"), forward_return.rename("forward_return")], axis=1).dropna()
    if len(aligned) < 5:
        return float("nan")
    bucket = max(1, len(aligned) // 5)
    ranked = aligned.sort_values("signal")
    bottom = ranked.head(bucket)["forward_return"].mean()
    top = ranked.tail(bucket)["forward_return"].mean()
    return float(top - bottom)


def run_backtest(
    panel: AlignedPanel,
    signal: MomentumReversalSignal,
    universe_config: UniverseConfig,
    portfolio_config: PortfolioConfig,
    backtest_config: BacktestConfig,
) -> BacktestResult:
    frame = panel.frame.sort_index()
    dates = panel.dates
    symbols = panel.symbols
    rebalance_dates = set(_compute_rebalance_dates(dates, portfolio_config.rebalance_frequency))

    current_weights = _empty_weights(symbols)
    weights_history: list[pd.Series] = []
    returns_history: list[float] = []
    gross_history: list[float] = []
    cost_history: list[float] = []
    turnover_history: list[float] = []
    signal_snapshots: dict[pd.Timestamp, pd.Series] = {}

    for date in dates:
        cross_section = frame.xs(date, level="date")
        asset_returns = cross_section["return_1d"].fillna(0.0).reindex(symbols).fillna(0.0)
        gross_return = float((current_weights * asset_returns).sum())
        drifted_weights = _drift_weights(current_weights, asset_returns)

        if date in rebalance_dates:
            trade_universe = build_universe(panel=panel, asof_date=date, config=universe_config)
            target_signal = signal.compute(panel, date).reindex(trade_universe).dropna()
            target_weights = construct_target_weights(
                signal=target_signal,
                current_weights=drifted_weights,
                long_n=portfolio_config.long_n,
                short_n=portfolio_config.short_n,
                gross_exposure=portfolio_config.gross_exposure,
                net_exposure=portfolio_config.net_exposure,
                max_abs_weight=portfolio_config.max_abs_weight,
                turnover_limit=portfolio_config.turnover_limit,
            ).reindex(symbols).fillna(0.0)
            turnover = float((target_weights - drifted_weights).abs().sum())
            trading_cost = float(backtest_config.one_way_cost_bps / 10_000.0 * turnover)
            current_weights = target_weights
            signal_snapshots[pd.Timestamp(date)] = target_signal
        else:
            turnover = 0.0
            trading_cost = 0.0
            current_weights = drifted_weights

        weights_history.append(current_weights.rename(date))
        returns_history.append(gross_return - trading_cost)
        gross_history.append(gross_return)
        cost_history.append(trading_cost)
        turnover_history.append(turnover)

    returns = pd.Series(returns_history, index=dates, name="net_return")
    gross_returns = pd.Series(gross_history, index=dates, name="gross_return")
    costs = pd.Series(cost_history, index=dates, name="cost")
    turnover = pd.Series(turnover_history, index=dates, name="turnover")
    weights = pd.DataFrame(weights_history).set_index(pd.Index(dates, name="date"))

    diagnostic_rows: list[dict[str, object]] = []
    ordered_rebalance_dates = sorted(signal_snapshots)
    signal_ics: dict[pd.Timestamp, float] = {}
    for start_date, end_date in zip(ordered_rebalance_dates[:-1], ordered_rebalance_dates[1:]):
        forward_return = _compute_forward_return(panel, start_date, end_date)
        sampled_signal = signal_snapshots[start_date].reindex(forward_return.index).dropna()
        aligned = pd.concat([sampled_signal.rename("signal"), forward_return], axis=1).dropna()
        if len(aligned) < 5 or aligned["signal"].nunique() < 2 or aligned["forward_return"].nunique() < 2:
            ic = np.nan
            spread = np.nan
        else:
            ic = float(aligned["signal"].corr(aligned["forward_return"], method="spearman"))
            spread = _compute_top_bottom_spread(aligned["signal"], aligned["forward_return"])
        signal_ics[start_date] = ic
        diagnostic_rows.append(
            {
                "date": start_date,
                "signal_name": signal.name,
                "rank_ic": ic,
                "top_bottom_spread": spread,
                "coverage": int(len(aligned)),
            }
        )

    signal_diagnostics = pd.DataFrame(diagnostic_rows).set_index("date").sort_index() if diagnostic_rows else pd.DataFrame()
    benchmark_history = frame.xs(backtest_config.benchmark_symbol, level="symbol") if backtest_config.benchmark_symbol in symbols else pd.DataFrame()
    benchmark_returns = benchmark_history["return_1d"].reindex(dates).fillna(0.0) if not benchmark_history.empty else pd.Series(0.0, index=dates)
    sector_map = frame.reset_index()[["symbol", "sector"]].drop_duplicates().set_index("symbol")["sector"].to_dict()
    metrics = summarize_metrics(
        returns=returns,
        turnover=turnover,
        costs=costs,
        signal_ics=pd.Series(signal_ics, name="rank_ic"),
        benchmark_returns=benchmark_returns,
        weights=weights,
        sector_map=sector_map,
    )
    report_state = "complete" if not signal_diagnostics.empty else "incomplete"
    return BacktestResult(
        returns=returns,
        gross_returns=gross_returns,
        costs=costs,
        turnover=turnover,
        weights=weights,
        signal_diagnostics=signal_diagnostics,
        metrics=metrics,
        report_state=report_state,
    )
