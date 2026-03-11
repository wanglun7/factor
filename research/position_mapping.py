from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import PositionMappingConfig


def _safe_corr(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if aligned.empty or aligned["left"].nunique() < 2 or aligned["right"].nunique() < 2:
        return 0.0
    corr = aligned["left"].corr(aligned["right"])
    return 0.0 if pd.isna(corr) else float(corr)


def _max_drawdown(returns: pd.Series) -> float:
    valid = returns.dropna()
    if valid.empty:
        return 0.0
    equity = (1.0 + valid).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


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


def _realized_annual_vol(returns: pd.Series, annualization: int) -> float:
    valid = returns.dropna()
    if len(valid) < 2:
        return 0.0
    return float(valid.std(ddof=0) * np.sqrt(annualization))


def _target_position(scaled_alpha: pd.Series, config: PositionMappingConfig) -> pd.Series:
    return (scaled_alpha * config.position_scale).clip(-config.max_abs_position, config.max_abs_position)


def _apply_band(target: pd.Series, band: float) -> pd.Series:
    realized: list[float] = []
    prev = 0.0
    for value in target.fillna(0.0).to_numpy(dtype=float):
        if abs(value - prev) < band:
            realized.append(prev)
        else:
            prev = value
            realized.append(prev)
    return pd.Series(realized, index=target.index, dtype=float)


def _compute_variant_frame(
    symbol_frame: pd.DataFrame,
    *,
    variant: str,
    config: PositionMappingConfig,
) -> pd.DataFrame:
    frame = symbol_frame.copy()
    frame["target_position"] = _target_position(frame["scaled_alpha"], config)
    frame["vol_scalar"] = 1.0

    if variant == "linear_target_only":
        frame["realized_position"] = frame["target_position"]
    elif variant == "linear_band":
        frame["realized_position"] = _apply_band(frame["target_position"], config.rebalance_band)
    elif variant == "linear_band_vol_target":
        lagged_annual_vol = frame[f"realized_vol_{config.vol_window}bar"].shift(1)
        lagged_annual_vol = lagged_annual_vol.clip(lower=config.min_annual_vol_floor)
        vol_scalar = (config.target_annual_vol / lagged_annual_vol).clip(upper=1.0)
        frame["vol_scalar"] = vol_scalar.fillna(0.0)
        vol_targeted = (frame["target_position"] * frame["vol_scalar"]).clip(
            -config.max_abs_position,
            config.max_abs_position,
        )
        frame["target_position"] = vol_targeted
        frame["realized_position"] = _apply_band(frame["target_position"], config.rebalance_band)
    else:
        raise ValueError(f"Unsupported position mapping variant: {variant}")

    frame["turnover"] = frame["realized_position"].diff().abs().fillna(frame["realized_position"].abs())
    frame["gross_return"] = frame["realized_position"] * frame["next_return_1bar"].fillna(0.0)
    frame["cost"] = frame["turnover"] * (config.one_way_cost_bps / 10000.0)
    frame["net_return"] = frame["gross_return"] - frame["cost"]
    frame["variant"] = variant
    return frame


def _variant_summary(
    frame: pd.DataFrame,
    *,
    config: PositionMappingConfig,
) -> dict[str, object]:
    net_returns = frame["net_return"]
    gross_returns = frame["gross_return"]
    total_gross = float((1.0 + gross_returns).prod() - 1.0) if not gross_returns.empty else 0.0
    total_net = float((1.0 + net_returns).prod() - 1.0) if not net_returns.empty else 0.0
    return {
        "variant": str(frame["variant"].iloc[0]),
        "scaled_alpha_to_target_corr": _safe_corr(frame["scaled_alpha"], frame["target_position"]),
        "scaled_alpha_to_realized_corr": _safe_corr(frame["scaled_alpha"], frame["realized_position"]),
        "target_to_realized_corr": _safe_corr(frame["target_position"], frame["realized_position"]),
        "mean_abs_position": float(frame["realized_position"].abs().mean()),
        "mean_turnover": float(frame["turnover"].mean()),
        "band_hold_ratio": float(
            (frame["realized_position"] == frame["realized_position"].shift(1)).mean()
        ) if len(frame) > 1 else 0.0,
        "vol_scalar_mean": float(frame["vol_scalar"].mean()),
        "gross_total_return": total_gross,
        "net_total_return": total_net,
        "annual_return": _annual_return(net_returns, config.annualization),
        "sharpe": _sharpe(net_returns, config.annualization),
        "max_drawdown": _max_drawdown(net_returns),
        "realized_annual_vol": _realized_annual_vol(net_returns, config.annualization),
        "cost_drag": total_gross - total_net,
    }


def _paper_horse_race(variant_summary: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    anchor_variant = "linear_target_only"
    anchor_row = variant_summary.loc[variant_summary["variant"] == anchor_variant].iloc[0]
    rows: list[dict[str, object]] = []
    for _, row in variant_summary.iterrows():
        variant = str(row["variant"])
        if variant == anchor_variant:
            verdict = "anchor"
        else:
            strong_pass = (
                float(row["sharpe"]) >= float(anchor_row["sharpe"])
                and float(row["net_total_return"]) >= 0.90 * float(anchor_row["net_total_return"])
                and float(row["mean_turnover"]) < float(anchor_row["mean_turnover"])
                and float(row["cost_drag"]) < float(anchor_row["cost_drag"])
            )
            robust_pass = (
                float(row["sharpe"]) > float(anchor_row["sharpe"])
                and float(row["net_total_return"]) >= 0.80 * float(anchor_row["net_total_return"])
                and float(row["realized_annual_vol"]) < float(anchor_row["realized_annual_vol"])
                and float(row["cost_drag"]) < float(anchor_row["cost_drag"])
            )
            verdict = "strong_win" if strong_pass else "robust_win" if robust_pass else "fail"
        rows.append(
            {
                **row.to_dict(),
                "anchor_variant": anchor_variant,
                "verdict": verdict,
            }
        )

    horse_race = pd.DataFrame(rows)
    strong_rows = horse_race.loc[horse_race["verdict"] == "strong_win"].sort_values(
        ["sharpe", "net_total_return"], ascending=[False, False]
    )
    robust_rows = horse_race.loc[horse_race["verdict"] == "robust_win"].sort_values(
        ["sharpe", "net_total_return"], ascending=[False, False]
    )
    if not strong_rows.empty:
        winner_variant = str(strong_rows.iloc[0]["variant"])
        winner_verdict = "strong_win"
    elif not robust_rows.empty:
        winner_variant = str(robust_rows.iloc[0]["variant"])
        winner_verdict = "robust_win"
    else:
        winner_variant = anchor_variant
        winner_verdict = "anchor_fallback"
    return horse_race, winner_variant, winner_verdict


def run_position_mapping(
    *,
    scaled_alpha_series: pd.DataFrame,
    source_name: str,
    market_frame: pd.DataFrame,
    config: PositionMappingConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    required_scaled = {"date", "symbol", "scaled_alpha", "forecast_return_30bar", "composite_score"}
    missing_scaled = required_scaled.difference(scaled_alpha_series.columns)
    if missing_scaled:
        raise ValueError(f"Scaled alpha series missing required columns: {sorted(missing_scaled)}")
    required_market = {"date", "symbol", "next_return_1bar", f"realized_vol_{config.vol_window}bar"}
    missing_market = required_market.difference(market_frame.columns)
    if missing_market:
        raise ValueError(f"Market frame missing required columns: {sorted(missing_market)}")

    merged = (
        scaled_alpha_series[["date", "symbol", "source_name", "composite_score", "forecast_return_30bar", "scaled_alpha"]]
        .merge(
            market_frame[["date", "symbol", "close", "next_return_1bar", f"realized_vol_{config.vol_window}bar"]],
            on=["date", "symbol"],
            how="left",
        )
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )

    variant_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for variant in ("linear_target_only", "linear_band", "linear_band_vol_target"):
        symbol_variant_frames: list[pd.DataFrame] = []
        for _, symbol_frame in merged.groupby("symbol", sort=True):
            symbol_variant_frames.append(_compute_variant_frame(symbol_frame, variant=variant, config=config))
        variant_frame = pd.concat(symbol_variant_frames, ignore_index=True).sort_values(["variant", "symbol", "date"])
        variant_frames.append(variant_frame)
        summaries.append(_variant_summary(variant_frame, config=config))

    series = pd.concat(variant_frames, ignore_index=True)
    series.to_parquet(target / "position_mapping_series.parquet", index=False)

    variant_summary = pd.DataFrame(summaries).sort_values("variant").reset_index(drop=True)
    variant_summary.to_csv(target / "position_mapping_variant_summary.csv", index=False)

    horse_race, official_variant, winner_verdict = _paper_horse_race(variant_summary)
    horse_race.to_csv(target / "position_mapping_horse_race.csv", index=False)
    official_row = horse_race.loc[horse_race["variant"] == official_variant].iloc[0]

    summary = pd.DataFrame(
        [
            {
                **official_row.to_dict(),
                "source_name": source_name,
                "position_scale": config.position_scale,
                "max_abs_position": config.max_abs_position,
                "rebalance_band": config.rebalance_band,
                "target_annual_vol": config.target_annual_vol,
                "min_annual_vol_floor": config.min_annual_vol_floor,
                "one_way_cost_bps": config.one_way_cost_bps,
                "winner_verdict": winner_verdict,
            }
        ]
    )
    summary.to_csv(target / "position_mapping_summary.csv", index=False)

    decision_log = "\n".join(
        [
            "# Position Mapping Decision Log",
            "",
            f"- source_name: `{source_name}`",
            "- anchor_variant: `linear_target_only`",
            f"- paper_winner_variant: `{official_variant}`",
            f"- paper_winner_verdict: `{winner_verdict}`",
            f"- scaled_alpha_to_realized_corr: `{float(official_row['scaled_alpha_to_realized_corr']):.4f}`",
            f"- net_total_return: `{float(official_row['net_total_return']):.6f}`",
            f"- sharpe: `{float(official_row['sharpe']):.4f}`",
            f"- realized_annual_vol: `{float(official_row['realized_annual_vol']):.4f}`",
            f"- mean_turnover: `{float(official_row['mean_turnover']):.6f}`",
            f"- band_hold_ratio: `{float(official_row['band_hold_ratio']):.4f}`",
            f"- vol_scalar_mean: `{float(official_row['vol_scalar_mean']):.4f}`",
        ]
    )
    (target / "position_mapping_decision_log.md").write_text(decision_log, encoding="utf-8")

    return {
        "series": series,
        "variant_summary": variant_summary,
        "horse_race": horse_race,
        "summary": summary,
        "source_name": source_name,
        "variant": official_variant,
        "verdict": winner_verdict,
    }
