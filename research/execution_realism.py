from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import ExecutionRealismConfig


def _annual_return(returns: pd.Series, annualization: int) -> float:
    valid = returns.dropna()
    if valid.empty:
        return 0.0
    mean_return = float(valid.mean())
    return float((1.0 + mean_return) ** annualization - 1.0) if mean_return > -1.0 else -1.0


def _sharpe(returns: pd.Series, annualization: int) -> float:
    valid = returns.dropna()
    if len(valid) < 2:
        return 0.0
    std = float(valid.std(ddof=0))
    if std <= 0.0:
        return 0.0
    return float(valid.mean() / std * np.sqrt(annualization))


def _max_drawdown(returns: pd.Series) -> float:
    valid = returns.dropna()
    if valid.empty:
        return 0.0
    equity = (1.0 + valid).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def _realized_annual_vol(returns: pd.Series, annualization: int) -> float:
    valid = returns.dropna()
    if len(valid) < 2:
        return 0.0
    return float(valid.std(ddof=0) * np.sqrt(annualization))


def _expanding_percentile_rank(values: pd.Series) -> pd.Series:
    valid_values = values.astype(float)
    output: list[float] = []
    history: list[float] = []
    for value in valid_values.tolist():
        if pd.isna(value):
            output.append(np.nan)
            continue
        sample = np.asarray(history + [float(value)], dtype=float)
        rank = float((sample <= float(value)).mean())
        output.append(rank)
        history.append(float(value))
    return pd.Series(output, index=values.index, dtype=float)


def _path_summary(frame: pd.DataFrame, *, path_name: str, annualization: int) -> dict[str, object]:
    net_returns = frame["net_return"]
    gross_returns = frame["gross_return"]
    return {
        "mapping_variant": str(frame["variant"].iloc[0]),
        "path_name": path_name,
        "gross_total_return": float((1.0 + gross_returns).prod() - 1.0) if not gross_returns.empty else 0.0,
        "net_total_return": float((1.0 + net_returns).prod() - 1.0) if not net_returns.empty else 0.0,
        "annual_return": _annual_return(net_returns, annualization),
        "sharpe": _sharpe(net_returns, annualization),
        "max_drawdown": _max_drawdown(net_returns),
        "realized_annual_vol": _realized_annual_vol(net_returns, annualization),
        "mean_turnover": float(frame["turnover"].mean()),
        "trade_frequency": float(frame["turnover"].gt(0).mean()),
        "mean_trade_size": float(frame.loc[frame["turnover"] > 0, "turnover"].mean()) if frame["turnover"].gt(0).any() else 0.0,
        "cost_drag": float(((1.0 + gross_returns).prod() - 1.0) - ((1.0 + net_returns).prod() - 1.0)) if not net_returns.empty else 0.0,
    }


def _build_path_frame(
    base: pd.DataFrame,
    *,
    path_name: str,
    lag_bars: int,
    use_state_cost: bool,
    config: ExecutionRealismConfig,
) -> pd.DataFrame:
    frame = base.copy()
    if lag_bars == 0:
        frame["executed_position"] = frame["paper_position"]
    else:
        frame["executed_position"] = frame["paper_position"].shift(lag_bars).fillna(0.0)
    frame["executed_turnover"] = frame["executed_position"].diff().abs().fillna(frame["executed_position"].abs())
    frame["turnover"] = frame["executed_turnover"]
    frame["gross_return"] = frame["executed_position"] * frame["next_return_1bar"].fillna(0.0)

    effective_cost_bps = pd.Series(config.base_one_way_cost_bps, index=frame.index, dtype=float)
    if use_state_cost:
        vol_rank = _expanding_percentile_rank(frame[f"realized_vol_{config.vol_window}bar"].shift(1))
        liquidity_rank = _expanding_percentile_rank(frame[config.liquidity_column].shift(1))
        effective_cost_bps = (
            config.base_one_way_cost_bps
            + config.vol_cost_multiplier_bps * vol_rank.fillna(0.0)
            + config.turnover_cost_multiplier_bps * frame["executed_turnover"].fillna(0.0)
            + config.liquidity_cost_multiplier_bps * liquidity_rank.fillna(0.0)
        )
    frame["effective_cost_bps"] = effective_cost_bps
    frame["cost"] = frame["executed_turnover"] * frame["effective_cost_bps"] / 10000.0
    frame["net_return"] = frame["gross_return"] - frame["cost"]
    frame["path_name"] = path_name
    return frame


def run_execution_realism(
    *,
    position_mapping_series: pd.DataFrame,
    source_name: str,
    market_frame: pd.DataFrame,
    config: ExecutionRealismConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    required_position = {"date", "symbol", "variant", "realized_position", "target_position"}
    missing_position = required_position.difference(position_mapping_series.columns)
    if missing_position:
        raise ValueError(f"Position mapping series missing required columns: {sorted(missing_position)}")
    required_market = {"date", "symbol", "next_return_1bar", f"realized_vol_{config.vol_window}bar", config.liquidity_column}
    missing_market = required_market.difference(market_frame.columns)
    if missing_market:
        raise ValueError(f"Market frame missing required columns: {sorted(missing_market)}")

    base = (
        position_mapping_series[["date", "symbol", "variant", "target_position", "realized_position"]]
        .rename(columns={"realized_position": "paper_position"})
        .merge(
            market_frame[["date", "symbol", "next_return_1bar", f"realized_vol_{config.vol_window}bar", config.liquidity_column]],
            on=["date", "symbol"],
            how="left",
        )
        .sort_values(["variant", "symbol", "date"])
        .reset_index(drop=True)
    )

    path_specs = [
        ("paper_position_path", 0, False),
        ("lag_1_execution", config.execution_lag_bars, False),
        ("lag_1_execution_with_state_cost", config.execution_lag_bars, True),
        ("lag_2_execution", 2, False),
        ("lag_2_execution_with_state_cost", 2, True),
    ]

    path_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for variant, variant_frame in base.groupby("variant", sort=True):
        for path_name, lag_bars, use_state_cost in path_specs:
            symbol_frames: list[pd.DataFrame] = []
            for _, symbol_frame in variant_frame.groupby("symbol", sort=True):
                symbol_frames.append(
                    _build_path_frame(
                        symbol_frame,
                        path_name=path_name,
                        lag_bars=lag_bars,
                        use_state_cost=use_state_cost,
                        config=config,
                    )
                )
            path_frame = pd.concat(symbol_frames, ignore_index=True).sort_values(["symbol", "date"])
            path_frame["variant"] = variant
            path_frames.append(path_frame)
            summaries.append(_path_summary(path_frame, path_name=path_name, annualization=config.annualization))

    series = pd.concat(path_frames, ignore_index=True)
    series.to_parquet(target / "execution_realism_series.parquet", index=False)

    path_summary = pd.DataFrame(summaries).sort_values(["mapping_variant", "path_name"]).reset_index(drop=True)
    path_summary.to_csv(target / "execution_realism_path_summary.csv", index=False)

    anchor_variant = "linear_target_only"
    variant_rows: list[dict[str, object]] = []
    for variant in sorted(path_summary["mapping_variant"].unique().tolist()):
        paper_row = path_summary.loc[
            (path_summary["mapping_variant"] == variant) & (path_summary["path_name"] == "paper_position_path")
        ].iloc[0]
        lag1_row = path_summary.loc[
            (path_summary["mapping_variant"] == variant) & (path_summary["path_name"] == "lag_1_execution")
        ].iloc[0]
        official_row = path_summary.loc[
            (path_summary["mapping_variant"] == variant) & (path_summary["path_name"] == "lag_1_execution_with_state_cost")
        ].iloc[0]
        lag2_row = path_summary.loc[
            (path_summary["mapping_variant"] == variant) & (path_summary["path_name"] == "lag_2_execution_with_state_cost")
        ].iloc[0]
        variant_rows.append(
            {
                **official_row.to_dict(),
                "paper_net_total_return": float(paper_row["net_total_return"]),
                "lag_1_net_total_return": float(lag1_row["net_total_return"]),
                "implementation_shortfall": float(paper_row["net_total_return"] - official_row["net_total_return"]),
                "execution_lag_drag": float(paper_row["net_total_return"] - lag1_row["net_total_return"]),
                "state_cost_drag": float(lag1_row["net_total_return"] - official_row["net_total_return"]),
                "delay_sensitivity_drag": float(official_row["net_total_return"] - lag2_row["net_total_return"]),
            }
        )

    variant_summary = pd.DataFrame(variant_rows).sort_values("mapping_variant").reset_index(drop=True)
    anchor_row = variant_summary.loc[variant_summary["mapping_variant"] == anchor_variant].iloc[0]
    race_rows: list[dict[str, object]] = []
    for _, row in variant_summary.iterrows():
        variant = str(row["mapping_variant"])
        if variant == anchor_variant:
            verdict = "anchor"
        else:
            strong_pass = (
                float(row["sharpe"]) >= float(anchor_row["sharpe"])
                and float(row["net_total_return"]) >= config.strong_relative_return_floor * float(anchor_row["net_total_return"])
                and float(row["mean_turnover"]) < float(anchor_row["mean_turnover"])
                and float(row["cost_drag"]) < float(anchor_row["cost_drag"])
            )
            robust_pass = (
                float(row["sharpe"]) > float(anchor_row["sharpe"])
                and float(row["net_total_return"]) >= config.robust_relative_return_floor * float(anchor_row["net_total_return"])
                and float(row["realized_annual_vol"]) < float(anchor_row["realized_annual_vol"])
                and float(row["cost_drag"]) < float(anchor_row["cost_drag"])
            )
            verdict = "strong_win" if strong_pass else "robust_win" if robust_pass else "fail"
        race_rows.append({**row.to_dict(), "anchor_variant": anchor_variant, "verdict": verdict})

    variant_summary = pd.DataFrame(race_rows).sort_values("mapping_variant").reset_index(drop=True)
    variant_summary.to_csv(target / "execution_realism_variant_summary.csv", index=False)

    strong_rows = variant_summary.loc[variant_summary["verdict"] == "strong_win"].sort_values(
        ["sharpe", "net_total_return"], ascending=[False, False]
    )
    robust_rows = variant_summary.loc[variant_summary["verdict"] == "robust_win"].sort_values(
        ["sharpe", "net_total_return"], ascending=[False, False]
    )
    if not strong_rows.empty:
        winner_row = strong_rows.iloc[0]
        winner_variant = str(winner_row["mapping_variant"])
        winner_verdict = "strong_win"
    elif not robust_rows.empty:
        winner_row = robust_rows.iloc[0]
        winner_variant = str(winner_row["mapping_variant"])
        winner_verdict = "robust_win"
    else:
        winner_row = anchor_row
        winner_variant = anchor_variant
        winner_verdict = "anchor_fallback"

    summary = pd.DataFrame(
        [
            {
                **winner_row.to_dict(),
                "source_name": source_name,
                "official_position_variant": winner_variant,
                "official_execution_variant": "lag_1_execution_with_state_cost",
                "winner_verdict": winner_verdict,
            }
        ]
    )
    summary.to_csv(target / "execution_realism_summary.csv", index=False)

    decision_log = "\n".join(
        [
            "# Execution Realism Decision Log",
            "",
            f"- source_name: `{source_name}`",
            f"- anchor_variant: `{anchor_variant}`",
            f"- official_position_variant: `{winner_variant}`",
            "- official_execution_variant: `lag_1_execution_with_state_cost`",
            f"- winner_verdict: `{winner_verdict}`",
            f"- paper_net_total_return: `{float(winner_row['paper_net_total_return']):.6f}`",
            f"- lag1_net_total_return: `{float(winner_row['lag_1_net_total_return']):.6f}`",
            f"- lag1_state_cost_net_total_return: `{float(winner_row['net_total_return']):.6f}`",
            f"- implementation_shortfall: `{float(winner_row['implementation_shortfall']):.6f}`",
            f"- execution_lag_drag: `{float(winner_row['execution_lag_drag']):.6f}`",
            f"- state_cost_drag: `{float(winner_row['state_cost_drag']):.6f}`",
            f"- delay_sensitivity_drag: `{float(winner_row['delay_sensitivity_drag']):.6f}`",
        ]
    )
    (target / "execution_realism_decision_log.md").write_text(decision_log, encoding="utf-8")

    return {
        "series": series,
        "path_summary": path_summary,
        "variant_summary": variant_summary,
        "summary": summary,
        "source_name": source_name,
        "variant": "lag_1_execution_with_state_cost",
        "position_variant": winner_variant,
        "verdict": winner_verdict,
    }
