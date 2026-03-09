from __future__ import annotations

import numpy as np
import pandas as pd


def compute_max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def compute_beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
    if aligned.empty or aligned.iloc[:, 1].var(ddof=0) == 0:
        return 0.0
    covariance = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    variance = aligned.iloc[:, 1].var(ddof=0)
    return float(covariance / variance)


def compute_sector_concentration(weights: pd.DataFrame, sector_map: dict[str, str]) -> tuple[float, float]:
    if weights.empty:
        return 0.0, 0.0
    sector_rows = []
    for _, row in weights.fillna(0.0).iterrows():
        per_sector: dict[str, float] = {}
        for symbol, weight in row.items():
            sector = sector_map.get(symbol, "unknown")
            # Use absolute exposure so long/short portfolios get a meaningful concentration signal.
            per_sector[sector] = per_sector.get(sector, 0.0) + abs(float(weight))
        sector_rows.append(per_sector)
    sector_frame = pd.DataFrame(sector_rows).fillna(0.0)
    herfindahl = (sector_frame.pow(2).sum(axis=1)).mean()
    max_sector_weight = sector_frame.max(axis=1).mean()
    return float(herfindahl), float(max_sector_weight)


def summarize_metrics(
    returns: pd.Series,
    turnover: pd.Series,
    costs: pd.Series,
    signal_ics: pd.Series,
    benchmark_returns: pd.Series,
    weights: pd.DataFrame | None = None,
    sector_map: dict[str, str] | None = None,
) -> dict[str, float]:
    cleaned_returns = returns.fillna(0.0)
    periods = len(cleaned_returns)
    if periods == 0:
        return {}

    annualization = 365
    total_return = float((1.0 + cleaned_returns).prod() - 1.0)
    annual_return = float((1.0 + total_return) ** (annualization / periods) - 1.0)
    annual_vol = float(cleaned_returns.std(ddof=0) * np.sqrt(annualization))
    sharpe = float(cleaned_returns.mean() / cleaned_returns.std(ddof=0) * np.sqrt(annualization)) if annual_vol else 0.0
    downside = cleaned_returns.where(cleaned_returns < 0.0, 0.0)
    downside_vol = float(downside.std(ddof=0) * np.sqrt(annualization))
    sortino = float(cleaned_returns.mean() / downside.std(ddof=0) * np.sqrt(annualization)) if downside_vol else 0.0
    max_drawdown = compute_max_drawdown(cleaned_returns)
    correlation = float(cleaned_returns.corr(benchmark_returns)) if not benchmark_returns.empty else 0.0
    beta = compute_beta(cleaned_returns, benchmark_returns)

    ic_mean = float(signal_ics.dropna().mean()) if not signal_ics.dropna().empty else 0.0
    ic_std = float(signal_ics.dropna().std(ddof=0)) if not signal_ics.dropna().empty else 0.0
    ic_ir = float(ic_mean / ic_std) if ic_std else 0.0

    sector_concentration = 0.0
    max_sector_weight = 0.0
    if weights is not None and sector_map:
        sector_concentration, max_sector_weight = compute_sector_concentration(weights, sector_map)

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": annual_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": float(annual_return / abs(max_drawdown)) if max_drawdown else 0.0,
        "average_turnover": float(turnover.mean()),
        "max_turnover": float(turnover.max()),
        "total_turnover": float(turnover.sum()),
        "total_cost": float(costs.sum()),
        "benchmark_correlation": correlation,
        "benchmark_beta": beta,
        "rank_ic_mean": ic_mean,
        "rank_ic_ir": ic_ir,
        "avg_sector_concentration": sector_concentration,
        "avg_max_sector_weight": max_sector_weight,
    }
