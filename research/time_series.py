from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app_config import TSBacktestConfig, TSResearchConfig, TSUniverseConfig
from models import AlignedPanel


@dataclass(frozen=True, slots=True)
class TSFactorSpec:
    name: str
    family: str
    hypothesis: str
    failure_mode: str
    required_columns: tuple[str, ...]


def _factor_specs() -> list[TSFactorSpec]:
    return [
        TSFactorSpec("tsmom_120bar", "trend", "约 20 天等价的趋势延续。", "震荡环境会反复止损。", ("ret_120bar",)),
        TSFactorSpec("tsmom_360bar", "trend", "约 60 天等价的更慢趋势。", "趋势反转时会滞后。", ("ret_360bar",)),
        TSFactorSpec("ema_gap_120_360", "trend", "快慢线偏离衡量 4h 趋势强度。", "高波动盘整期容易失真。", ("ema_120", "ema_360")),
        TSFactorSpec("breakout_360bar", "trend", "突破长区间后存在继续扩散。", "假突破多时失效。", ("breakout_360bar",)),
        TSFactorSpec("rev_6bar_voladj", "reversal", "约 1 天超调后的回吐。", "强趋势下会继续走。", ("ret_6bar", "realized_vol_120bar")),
        TSFactorSpec("rev_18bar_voladj", "reversal", "约 3 天超调后的回吐。", "趋势市会失效。", ("ret_18bar", "realized_vol_120bar")),
        TSFactorSpec("streak_reversal_30bar", "reversal", "约 5 天连续单边后的回吐。", "单边行情会继续强化。", ("ret_30bar", "up_bar_count_30", "down_bar_count_30")),
    ]


def _annualized_return(returns: pd.Series, annualization: int) -> float:
    clean = returns.dropna()
    if clean.empty:
        return 0.0
    compounded = float((1.0 + clean).prod())
    years = max(len(clean) / annualization, 1.0 / annualization)
    return float(compounded ** (1.0 / years) - 1.0)


def _max_drawdown(returns: pd.Series) -> float:
    clean = returns.fillna(0.0)
    equity = (1.0 + clean).cumprod()
    peaks = equity.cummax()
    drawdown = equity / peaks - 1.0
    return float(drawdown.min()) if not drawdown.empty else 0.0


def _sharpe_ratio(returns: pd.Series, annualization: int) -> float:
    clean = returns.dropna()
    if clean.empty:
        return 0.0
    std = float(clean.std(ddof=0))
    if std == 0.0 or np.isnan(std):
        return 0.0
    return float(clean.mean() / std * np.sqrt(annualization))


def _sortino_ratio(returns: pd.Series, annualization: int) -> float:
    clean = returns.dropna()
    if clean.empty:
        return 0.0
    downside = clean.clip(upper=0.0)
    downside_std = float(np.sqrt((downside.pow(2).mean())))
    if downside_std == 0.0 or np.isnan(downside_std):
        return 0.0
    return float(clean.mean() / downside_std * np.sqrt(annualization))


def _newey_west_tstat(returns: pd.Series, lags: int = 12) -> float:
    clean = returns.dropna().astype(float).to_numpy()
    n = len(clean)
    if n < 20:
        return 0.0
    centered = clean - clean.mean()
    gamma0 = float(np.dot(centered, centered) / n)
    variance = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        weight = 1.0 - lag / (lags + 1.0)
        gamma = float(np.dot(centered[lag:], centered[:-lag]) / n)
        variance += 2.0 * weight * gamma
    if variance <= 0.0 or np.isnan(variance):
        return 0.0
    se = np.sqrt(variance / n)
    if se == 0.0 or np.isnan(se):
        return 0.0
    return float(clean.mean() / se)


def _robust_zscore_by_symbol(values: pd.Series, window: int, min_periods: int) -> pd.Series:
    def _transform(series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        median = numeric.rolling(window, min_periods=min_periods).median()
        mad = numeric.rolling(window, min_periods=min_periods).apply(
            lambda arr: float(np.median(np.abs(arr - np.median(arr)))),
            raw=True,
        )
        scale = (1.4826 * mad).replace(0.0, np.nan)
        return ((numeric - median) / scale).replace([np.inf, -np.inf], np.nan)

    return values.groupby(level="symbol", group_keys=False).transform(_transform)


def _map_positions(zscores: pd.Series, entry_z: float, exit_z: float) -> pd.Series:
    out = pd.Series(0.0, index=zscores.index, dtype=float)
    for _, series in zscores.groupby(level="symbol", sort=False):
        previous = 0.0
        positions: list[float] = []
        for value in series.to_numpy():
            if np.isnan(value):
                position = previous
            elif value >= entry_z:
                position = 1.0
            elif value <= -entry_z:
                position = -1.0
            elif abs(value) < exit_z:
                position = 0.0
            else:
                position = previous
            positions.append(position)
            previous = position
        out.loc[series.index] = positions
    return out


def _build_factor_values(panel: AlignedPanel) -> pd.DataFrame:
    frame = panel.frame.copy()
    frame["tsmom_120bar"] = np.sign(frame["ret_120bar"])
    frame["tsmom_360bar"] = np.sign(frame["ret_360bar"])
    frame["ema_gap_120_360"] = frame["ema_120"] / frame["ema_360"] - 1.0
    frame["rev_6bar_voladj"] = -frame["ret_6bar"] / frame["realized_vol_120bar"].replace(0.0, np.nan)
    frame["rev_18bar_voladj"] = -frame["ret_18bar"] / frame["realized_vol_120bar"].replace(0.0, np.nan)
    frame["streak_reversal_30bar"] = -frame["ret_30bar"] * np.sign(frame["up_bar_count_30"] - frame["down_bar_count_30"])
    return frame


def _forward_returns(panel: AlignedPanel, horizon: int) -> pd.Series:
    close = panel.frame["close"].unstack("symbol").sort_index()
    forward = close.shift(-horizon) / close - 1.0
    try:
        return forward.stack(future_stack=True).rename(f"forward_return_{horizon}bar")
    except TypeError:
        return forward.stack(dropna=False).rename(f"forward_return_{horizon}bar")


def _eligible_symbols(panel: AlignedPanel, config: TSUniverseConfig, min_history_bars: int) -> list[str]:
    available = set(panel.symbols)
    requested = [symbol for symbol in config.symbols if symbol in available]
    eligible: list[str] = []
    for symbol in requested:
        history = panel.history_for_symbol(symbol)
        if len(history) >= min_history_bars:
            eligible.append(symbol)
    return eligible


def _prediction_buckets(zscores: pd.Series, forward_returns: pd.Series, factor_name: str, horizon: int) -> pd.DataFrame:
    aligned = pd.concat([zscores.rename("zscore"), forward_returns.rename("forward_return")], axis=1).dropna()
    if aligned.empty:
        return pd.DataFrame(columns=["factor", "horizon", "bucket", "observations", "mean_forward_return", "hit_ratio"])
    bins = [-np.inf, -0.75, -0.25, 0.25, 0.75, np.inf]
    labels = ["short", "short_hold", "flat", "long_hold", "long"]
    aligned["bucket"] = pd.cut(aligned["zscore"], bins=bins, labels=labels, include_lowest=True)
    rows: list[dict[str, object]] = []
    for bucket, group in aligned.groupby("bucket", observed=True):
        rows.append(
            {
                "factor": factor_name,
                "horizon": horizon,
                "bucket": str(bucket),
                "observations": int(len(group)),
                "mean_forward_return": float(group["forward_return"].mean()),
                "hit_ratio": float((group["forward_return"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _asset_strategy_metrics(history: pd.DataFrame, annualization: int, cost_rate: float) -> tuple[pd.DataFrame, dict[str, float]]:
    ordered = history.sort_index().copy()
    ordered["turnover"] = ordered["position"].diff().abs().fillna(ordered["position"].abs())
    ordered["gross_return"] = ordered["position"] * ordered["next_return_1bar"]
    ordered["cost"] = ordered["turnover"] * cost_rate
    ordered["net_return"] = ordered["gross_return"] - ordered["cost"]
    metrics = {
        "total_return": float((1.0 + ordered["net_return"].fillna(0.0)).prod() - 1.0),
        "annual_return": _annualized_return(ordered["net_return"], annualization),
        "sharpe": _sharpe_ratio(ordered["net_return"], annualization),
        "sortino": _sortino_ratio(ordered["net_return"], annualization),
        "max_drawdown": _max_drawdown(ordered["net_return"]),
        "mean_turnover": float(ordered["turnover"].mean()),
    }
    return ordered, metrics


def _aggregate_panel_strategy(factor_frame: pd.DataFrame, annualization: int, cost_rate: float) -> tuple[pd.DataFrame, dict[str, float]]:
    rows: list[dict[str, object]] = []
    contributions: list[dict[str, object]] = []
    previous_weights = pd.Series(dtype=float)
    for date, group in factor_frame.groupby("date", sort=True):
        working = group.loc[group["position"] != 0].copy()
        if working.empty:
            rows.append({"date": date, "gross_return": 0.0, "cost": 0.0, "net_return": 0.0, "turnover": 0.0})
            previous_weights = pd.Series(dtype=float)
            continue
        inv_vol = 1.0 / working["realized_vol_120bar"].replace(0.0, np.nan)
        scaled = (working["position"] * inv_vol).replace([np.inf, -np.inf], np.nan).dropna()
        if scaled.empty:
            rows.append({"date": date, "gross_return": 0.0, "cost": 0.0, "net_return": 0.0, "turnover": 0.0})
            previous_weights = pd.Series(dtype=float)
            continue
        weight_map = working.loc[scaled.index, "symbol"]
        weights = scaled / scaled.abs().sum()
        weights.index = weight_map.to_list()
        weights = weights.groupby(level=0).sum()
        aligned_prev = previous_weights.reindex(weights.index.union(previous_weights.index), fill_value=0.0)
        aligned_curr = weights.reindex(weights.index.union(previous_weights.index), fill_value=0.0)
        turnover = float((aligned_curr - aligned_prev).abs().sum())
        returns = working.set_index("symbol").loc[weights.index, "next_return_1bar"]
        gross_return = float((weights * returns).sum())
        cost = turnover * cost_rate
        net_return = gross_return - cost
        rows.append({"date": date, "gross_return": gross_return, "cost": cost, "net_return": net_return, "turnover": turnover})
        for symbol, weight in weights.items():
            contributions.append({"date": date, "symbol": symbol, "pnl_contribution": float(weight * returns.loc[symbol])})
        previous_weights = weights

    panel_returns = pd.DataFrame(rows).set_index("date").sort_index()
    contribution_frame = pd.DataFrame(contributions)
    total_pnl = float(contribution_frame["pnl_contribution"].sum()) if not contribution_frame.empty else 0.0
    max_share = 0.0
    positive_assets = 0
    if not contribution_frame.empty:
        by_symbol = contribution_frame.groupby("symbol")["pnl_contribution"].sum()
        positive_assets = int((by_symbol > 0).sum())
        if total_pnl != 0.0:
            max_share = float((by_symbol.abs() / abs(total_pnl)).max())
    panel_returns["year"] = panel_returns.index.year
    positive_years = int((panel_returns.groupby("year")["net_return"].sum() > 0).sum()) if not panel_returns.empty else 0
    metrics = {
        "total_return": float((1.0 + panel_returns["net_return"].fillna(0.0)).prod() - 1.0) if not panel_returns.empty else 0.0,
        "annual_return": _annualized_return(panel_returns["net_return"], annualization) if not panel_returns.empty else 0.0,
        "sharpe": _sharpe_ratio(panel_returns["net_return"], annualization) if not panel_returns.empty else 0.0,
        "sortino": _sortino_ratio(panel_returns["net_return"], annualization) if not panel_returns.empty else 0.0,
        "max_drawdown": _max_drawdown(panel_returns["net_return"]) if not panel_returns.empty else 0.0,
        "newey_west_tstat": _newey_west_tstat(panel_returns["net_return"]) if not panel_returns.empty else 0.0,
        "mean_turnover": float(panel_returns["turnover"].mean()) if not panel_returns.empty else 0.0,
        "positive_assets": positive_assets,
        "positive_years": positive_years,
        "max_symbol_pnl_share": max_share,
    }
    return panel_returns.drop(columns=["year"], errors="ignore"), metrics


def _decision(metrics: dict[str, float], universe_size: int) -> tuple[str, list[str]]:
    failures: list[str] = []
    if metrics["sharpe"] < 0.8:
        failures.append("sharpe<0.80")
    if metrics["newey_west_tstat"] < 2.0:
        failures.append("nw_tstat<2.00")
    if metrics["positive_assets"] < min(8, universe_size):
        failures.append(f"positive_assets<{min(8, universe_size)}")
    if metrics["positive_years"] < 3:
        failures.append("positive_years<3")
    if metrics["max_symbol_pnl_share"] > 0.35:
        failures.append("max_symbol_pnl_share>0.35")
    return ("accepted", failures) if not failures else ("rejected", failures)


def _per_factor_history(
    factor_frame: pd.DataFrame,
    factor: TSFactorSpec,
    panel: AlignedPanel,
    config: TSResearchConfig,
    universe: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_signal = factor_frame[factor.name]
    zscore = _robust_zscore_by_symbol(raw_signal, config.signal_z_window, config.signal_z_min_periods)
    position = _map_positions(zscore, config.entry_z, config.exit_z)
    working = factor_frame.loc[factor_frame.index.get_level_values("symbol").isin(universe)].copy()
    working["raw_signal"] = raw_signal.reindex(working.index)
    working["zscore"] = zscore.reindex(working.index)
    working["position"] = position.reindex(working.index).fillna(0.0)
    working = (
        working.groupby(level="symbol", group_keys=False)
        .apply(lambda frame: frame.iloc[config.min_history_bars :].copy())
        .sort_index()
    )
    strategy = working.reset_index()[["date", "symbol", "close", "next_return_1bar", "position", "realized_vol_120bar"]].copy()
    return working, strategy


def run_ts_factor_research_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    research_config: TSResearchConfig,
    backtest_config: TSBacktestConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    factor_frame = _build_factor_values(panel).reset_index()
    universe = _eligible_symbols(panel, universe_config, research_config.min_history_bars)
    cost_rate = research_config.one_way_cost_bps / 10_000.0

    summary_rows: list[dict[str, object]] = []
    asset_rows: list[dict[str, object]] = []
    yearly_rows: list[dict[str, object]] = []
    bucket_frames: list[pd.DataFrame] = []
    strategy_rows: list[dict[str, object]] = []
    decisions: list[tuple[str, str, list[str], TSFactorSpec]] = []

    for spec in _factor_specs():
        history, strategy = _per_factor_history(factor_frame.set_index(["date", "symbol"]), spec, panel, research_config, universe)
        valid_history = history.dropna(subset=["zscore", "raw_signal"])
        if valid_history.empty:
            decisions.append((spec.name, "rejected", ["no_valid_history"], spec))
            summary_rows.append(
                {
                    "factor": spec.name,
                    "family": spec.family,
                    "primary_horizon": research_config.primary_horizon,
                    "observations": 0,
                    "valid_assets": 0,
                    "strategy_sharpe": 0.0,
                    "strategy_newey_west_tstat": 0.0,
                    "strategy_annual_return": 0.0,
                    "strategy_total_return": 0.0,
                    "primary_bucket_spread": 0.0,
                    "decision": "rejected",
                }
            )
            continue

        primary_forward = _forward_returns(panel, research_config.primary_horizon).reindex(valid_history.index)
        primary_bucket_frame = _prediction_buckets(valid_history["zscore"], primary_forward, spec.name, research_config.primary_horizon)
        bucket_frames.append(primary_bucket_frame)
        bucket_lookup = primary_bucket_frame.set_index("bucket") if not primary_bucket_frame.empty else pd.DataFrame()
        long_mean = float(bucket_lookup.loc["long", "mean_forward_return"]) if "long" in bucket_lookup.index else 0.0
        short_mean = float(bucket_lookup.loc["short", "mean_forward_return"]) if "short" in bucket_lookup.index else 0.0
        bucket_spread = long_mean - short_mean

        for symbol in universe:
            symbol_history = strategy.loc[strategy["symbol"] == symbol].set_index("date")
            if symbol_history.empty:
                continue
            _, asset_metrics = _asset_strategy_metrics(symbol_history, research_config.annualization, cost_rate)
            asset_rows.append(
                {
                    "factor": spec.name,
                    "symbol": symbol,
                    "total_return": asset_metrics["total_return"],
                    "annual_return": asset_metrics["annual_return"],
                    "sharpe": asset_metrics["sharpe"],
                    "sortino": asset_metrics["sortino"],
                    "max_drawdown": asset_metrics["max_drawdown"],
                    "mean_turnover": asset_metrics["mean_turnover"],
                }
            )

        panel_returns, panel_metrics = _aggregate_panel_strategy(strategy, research_config.annualization, cost_rate)
        decision_state, failures = _decision(panel_metrics, len(universe))
        decisions.append((spec.name, decision_state, failures, spec))
        strategy_rows.append(
            {
                "factor": spec.name,
                "total_return": panel_metrics["total_return"],
                "annual_return": panel_metrics["annual_return"],
                "sharpe": panel_metrics["sharpe"],
                "sortino": panel_metrics["sortino"],
                "max_drawdown": panel_metrics["max_drawdown"],
                "newey_west_tstat": panel_metrics["newey_west_tstat"],
                "mean_turnover": panel_metrics["mean_turnover"],
                "positive_assets": panel_metrics["positive_assets"],
                "positive_years": panel_metrics["positive_years"],
                "max_symbol_pnl_share": panel_metrics["max_symbol_pnl_share"],
                "decision": decision_state,
            }
        )
        if not panel_returns.empty:
            yearly = panel_returns.assign(year=panel_returns.index.year).groupby("year").agg(
                total_return=("net_return", lambda values: float((1.0 + values.fillna(0.0)).prod() - 1.0)),
                annual_return=("net_return", lambda values: _annualized_return(values, research_config.annualization)),
                sharpe=("net_return", lambda values: _sharpe_ratio(values, research_config.annualization)),
                mean_turnover=("turnover", "mean"),
            )
            for _, row in yearly.reset_index().iterrows():
                yearly_rows.append(
                    {
                        "factor": spec.name,
                        "year": int(row["year"]),
                        "total_return": row["total_return"],
                        "annual_return": row["annual_return"],
                        "sharpe": row["sharpe"],
                        "mean_turnover": row["mean_turnover"],
                    }
                )

        summary_rows.append(
            {
                "factor": spec.name,
                "family": spec.family,
                "primary_horizon": research_config.primary_horizon,
                "observations": int(len(valid_history)),
                "valid_assets": int(len(strategy["symbol"].unique())),
                "strategy_sharpe": panel_metrics["sharpe"],
                "strategy_newey_west_tstat": panel_metrics["newey_west_tstat"],
                "strategy_annual_return": panel_metrics["annual_return"],
                "strategy_total_return": panel_metrics["total_return"],
                "primary_bucket_spread": bucket_spread,
                "decision": decision_state,
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(["decision", "strategy_sharpe"], ascending=[True, False])
    asset_summary = pd.DataFrame(asset_rows).sort_values(["factor", "symbol"])
    yearly_summary = pd.DataFrame(yearly_rows).sort_values(["factor", "year"])
    bucket_summary = pd.concat(bucket_frames, ignore_index=True) if bucket_frames else pd.DataFrame(columns=["factor", "horizon", "bucket", "observations", "mean_forward_return", "hit_ratio"])
    strategy_summary = pd.DataFrame(strategy_rows).sort_values(["decision", "sharpe"], ascending=[True, False])

    summary.to_csv(target / "ts4h_factor_summary.csv", index=False)
    asset_summary.to_csv(target / "ts4h_factor_asset_summary.csv", index=False)
    yearly_summary.to_csv(target / "ts4h_factor_yearly_summary.csv", index=False)
    bucket_summary.to_csv(target / "ts4h_factor_bucket_returns.csv", index=False)
    strategy_summary.to_csv(target / "ts4h_factor_strategy_summary.csv", index=False)

    decision_lines = [
        "# Time-Series 4h Factor Decision Log",
        "",
        f"- Universe: {', '.join(universe)}",
        f"- Primary horizon: {research_config.primary_horizon} bars",
        f"- Canonical mapping: entry {research_config.entry_z}, exit {research_config.exit_z}, robust-z window {research_config.signal_z_window}",
        "",
        "## Decisions",
    ]
    for factor_name, decision_state, failures, spec in decisions:
        suffix = f" ({', '.join(failures)})" if failures else ""
        decision_lines.extend(
            [
                f"- `{factor_name}`: {decision_state}{suffix}",
                f"  mechanism: {spec.hypothesis}",
                f"  failure_mode: {spec.failure_mode}",
            ]
        )
    (target / "ts4h_factor_decision_log.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

    return {
        "state": "complete",
        "output_dir": str(target),
        "factors": [spec.name for spec in _factor_specs()],
        "accepted_factors": summary.loc[summary["decision"] == "accepted", "factor"].tolist() if not summary.empty else [],
        "artifacts": {
            "ts4h_factor_summary": "ts4h_factor_summary.csv",
            "ts4h_factor_asset_summary": "ts4h_factor_asset_summary.csv",
            "ts4h_factor_yearly_summary": "ts4h_factor_yearly_summary.csv",
            "ts4h_factor_bucket_returns": "ts4h_factor_bucket_returns.csv",
            "ts4h_factor_strategy_summary": "ts4h_factor_strategy_summary.csv",
            "ts4h_factor_decision_log": "ts4h_factor_decision_log.md",
        },
    }


def run_ts_walkforward_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    research_config: TSResearchConfig,
    backtest_config: TSBacktestConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    factor_frame = _build_factor_values(panel).reset_index()
    universe = _eligible_symbols(panel, universe_config, research_config.min_history_bars)
    cost_rate = research_config.one_way_cost_bps / 10_000.0
    years = sorted(panel.dates.year.unique())
    if len(years) < 2:
        raise ValueError("Walkforward requires at least two natural years of 4h data.")

    split_rows: list[dict[str, object]] = []
    factor_rows: list[dict[str, object]] = []
    for spec in _factor_specs():
        _, strategy = _per_factor_history(factor_frame.set_index(["date", "symbol"]), spec, panel, research_config, universe)
        for test_year in years[1:]:
            test_frame = strategy.loc[pd.to_datetime(strategy["date"]).dt.year == test_year].copy()
            if test_frame.empty:
                continue
            _, panel_metrics = _aggregate_panel_strategy(test_frame, research_config.annualization, cost_rate)
            split_rows.append(
                {
                    "factor": spec.name,
                    "train_start": int(years[0]),
                    "train_end": int(test_year - 1),
                    "test_year": int(test_year),
                    "total_return": panel_metrics["total_return"],
                    "annual_return": panel_metrics["annual_return"],
                    "sharpe": panel_metrics["sharpe"],
                    "newey_west_tstat": panel_metrics["newey_west_tstat"],
                    "mean_turnover": panel_metrics["mean_turnover"],
                    "positive_assets": panel_metrics["positive_assets"],
                }
            )
        factor_splits = pd.DataFrame([row for row in split_rows if row["factor"] == spec.name])
        if factor_splits.empty:
            continue
        factor_rows.append(
            {
                "factor": spec.name,
                "mean_test_return": float(factor_splits["total_return"].mean()),
                "mean_test_sharpe": float(factor_splits["sharpe"].mean()),
                "positive_test_years": int((factor_splits["total_return"] > 0).sum()),
                "test_years": int(len(factor_splits)),
            }
        )

    split_summary = pd.DataFrame(split_rows).sort_values(["factor", "test_year"])
    factor_summary = pd.DataFrame(factor_rows).sort_values(["mean_test_sharpe", "mean_test_return"], ascending=False)
    split_summary.to_csv(target / "ts4h_walkforward_splits.csv", index=False)
    factor_summary.to_csv(target / "ts4h_walkforward_summary.csv", index=False)

    return {
        "state": "complete",
        "output_dir": str(target),
        "artifacts": {
            "ts4h_walkforward_splits": "ts4h_walkforward_splits.csv",
            "ts4h_walkforward_summary": "ts4h_walkforward_summary.csv",
        },
    }
