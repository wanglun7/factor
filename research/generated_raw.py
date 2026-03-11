from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import RawGenerationConfig
from models import AlignedPanel
from research.raw_generators.spec_builder import GeneratedDescriptorSpec, build_generated_specs
from research.rule_generators.spec_builder import GeneratedRuleSpec, build_generated_rule_specs
from research.signal_metrics import forward_return, spread_for_predictor


def _base_frame(panel: AlignedPanel, symbols: list[str]) -> pd.DataFrame:
    frame = panel.frame.reset_index()
    frame = frame.loc[frame["symbol"].isin(symbols)].copy()
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def _rolling_mean(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def _descriptor_series(frame: pd.DataFrame, spec: GeneratedDescriptorSpec) -> pd.Series:
    window = spec.horizon_window
    if spec.descriptor_id == "return":
        return frame[f"ret_{window}bar"]
    if spec.descriptor_id == "realized_volatility":
        return frame[f"realized_vol_{window}bar"]
    if spec.descriptor_id == "dollar_volume":
        return frame[f"avg_dollar_volume_{window}bar"]
    if spec.descriptor_id == "amihud":
        return frame[f"amihud_{window}bar"]
    if spec.descriptor_id == "funding":
        base = frame["funding_rate_lag1"]
        if window == 1:
            return base
        return base.groupby(frame["symbol"]).transform(lambda values: values.rolling(window, min_periods=window).mean())
    if spec.descriptor_id == "basis":
        base = (frame["close"] - frame["spot_close"]) / frame["spot_close"].replace(0.0, np.nan)
        if window == 1:
            return base
        return base.groupby(frame["symbol"]).transform(lambda values: values.rolling(window, min_periods=window).mean())
    if spec.descriptor_id == "premium":
        base = (frame["close"] - frame["index_close"]) / frame["index_close"].replace(0.0, np.nan) / 24.0
        if window == 1:
            return base
        return base.groupby(frame["symbol"]).transform(lambda values: values.rolling(window, min_periods=window).mean())
    raise ValueError(f"Unsupported descriptor id: {spec.descriptor_id}")


def _apply_descriptor_transform(frame: pd.DataFrame, base_values: pd.Series, spec: GeneratedDescriptorSpec) -> pd.Series:
    grouped = base_values.groupby(frame["symbol"])
    window = spec.horizon_window
    if spec.transform_id == "level":
        return base_values
    if spec.transform_id == "change":
        return base_values - grouped.shift(window)
    if spec.transform_id == "deviation":
        return base_values - grouped.transform(lambda values: values.rolling(window, min_periods=window).mean())
    if spec.transform_id == "ratio":
        baseline = grouped.transform(lambda values: values.rolling(window, min_periods=window).mean())
        return base_values / baseline.replace(0.0, np.nan) - 1.0
    if spec.transform_id == "percentile":
        return grouped.transform(lambda values: values.rolling(window, min_periods=window).rank(pct=True))
    if spec.transform_id == "vol_adjusted":
        return base_values / frame["realized_vol_120bar"].replace(0.0, np.nan)
    raise ValueError(f"Unsupported transform id: {spec.transform_id}")


def _lagged_close(frame: pd.DataFrame, window: int) -> pd.Series:
    return frame.groupby("symbol", group_keys=False)["close"].shift(window)


def _sma(frame: pd.DataFrame, window: int) -> pd.Series:
    return frame.groupby("symbol", group_keys=False)["close"].transform(
        lambda values: values.shift(1).rolling(window, min_periods=window).mean()
    )


def _ema(frame: pd.DataFrame, window: int) -> pd.Series:
    return frame.groupby("symbol", group_keys=False)["close"].transform(
        lambda values: values.shift(1).ewm(span=window, adjust=False, min_periods=window).mean()
    )


def _rolling_max(frame: pd.DataFrame, window: int) -> pd.Series:
    return frame.groupby("symbol", group_keys=False)["close"].transform(
        lambda values: values.shift(1).rolling(window, min_periods=window).max()
    )


def _rolling_min(frame: pd.DataFrame, window: int) -> pd.Series:
    return frame.groupby("symbol", group_keys=False)["close"].transform(
        lambda values: values.shift(1).rolling(window, min_periods=window).min()
    )


def _compute_rule_values(frame: pd.DataFrame, spec: GeneratedRuleSpec) -> pd.Series:
    close = frame["close"]
    if spec.form_id == "price_above_sma":
        return pd.Series(np.where(close > _sma(frame, spec.mapped_window_4h), 1.0, 0.0), index=frame.index)
    if spec.form_id == "price_above_ema":
        return pd.Series(np.where(close > _ema(frame, spec.mapped_window_4h), 1.0, 0.0), index=frame.index)
    if spec.form_id == "sma_crossover":
        short = _sma(frame, int(spec.short_window))
        long = _sma(frame, int(spec.long_window))
        return pd.Series(np.where(short > long, 1.0, 0.0), index=frame.index)
    if spec.form_id == "ema_crossover":
        short = _ema(frame, int(spec.short_window))
        long = _ema(frame, int(spec.long_window))
        return pd.Series(np.where(short > long, 1.0, 0.0), index=frame.index)
    if spec.form_id == "breakout_high_low":
        resistance = _rolling_max(frame, spec.mapped_window_4h)
        support = _rolling_min(frame, spec.mapped_window_4h)
        return pd.Series(np.where(close > resistance, 1.0, np.where(close < support, -1.0, 0.0)), index=frame.index)
    if spec.form_id == "price_filter_from_lag":
        lagged = _lagged_close(frame, spec.mapped_window_4h)
        change = close / lagged.replace(0.0, np.nan) - 1.0
        threshold = float(spec.threshold_bps) / 10000.0
        return pd.Series(np.where(change > threshold, 1.0, np.where(change < -threshold, -1.0, 0.0)), index=frame.index)
    raise ValueError(f"Unsupported rule form: {spec.form_id}")


def _raw_summary(
    catalog: pd.DataFrame,
    raw_frame: pd.DataFrame,
    primary_horizon: int,
) -> pd.DataFrame:
    base_frame = raw_frame.reset_index()
    forward_0 = forward_return(base_frame, primary_horizon, 0)
    forward_1 = forward_return(base_frame, primary_horizon, 1)
    forward_2 = forward_return(base_frame, primary_horizon, 2)
    rows: list[dict[str, object]] = []
    for row in catalog.itertuples(index=False):
        values = raw_frame[row.name]
        rows.append(
            {
                **row._asdict(),
                "delay_0_spread": spread_for_predictor(values, forward_0, row.predictor_type),
                "delay_1_spread": spread_for_predictor(values, forward_1, row.predictor_type),
                "delay_2_spread": spread_for_predictor(values, forward_2, row.predictor_type),
            }
        )
    return pd.DataFrame(rows).sort_values(["generator_line", "family", "name"]).reset_index(drop=True)


def build_generated_raw(
    panel: AlignedPanel,
    config: RawGenerationConfig,
    line: str,
) -> dict[str, pd.DataFrame | list[str]]:
    symbols: set[str] = set()
    frames: list[pd.DataFrame] = []
    catalogs: list[pd.DataFrame] = []

    if line in {"descriptor", "both"}:
        descriptor_symbols = [symbol for symbol in config.descriptor.symbols if symbol in panel.symbols]
        if descriptor_symbols:
            symbols.update(descriptor_symbols)
            frame = _base_frame(panel, descriptor_symbols)
            specs = build_generated_specs(config.descriptor)
            for spec in specs:
                base_values = _descriptor_series(frame, spec)
                frame[spec.name] = _apply_descriptor_transform(frame, base_values, spec)
            frames.append(frame.set_index(["date", "symbol"]).sort_index())
            catalogs.append(
                pd.DataFrame(
                    [
                        {
                            "name": spec.name,
                            "generator_line": spec.generator_line,
                            "family": spec.descriptor_family,
                            "predictor_type": spec.predictor_type,
                            "alpha_direction_policy": spec.alpha_direction_policy,
                            "score_method_family": spec.score_method_family,
                            "descriptor_id": spec.descriptor_id,
                            "transform_id": spec.transform_id,
                            "horizon_id": spec.horizon_id,
                            "horizon_group": spec.horizon_group,
                            "native_window": np.nan,
                            "mapped_window_4h": spec.horizon_window,
                            "mapping_method": spec.horizon_unit,
                            "threshold_bps": np.nan,
                            "short_window": np.nan,
                            "long_window": np.nan,
                        }
                        for spec in specs
                    ]
                )
            )

    if line in {"rule", "both"}:
        rule_symbols = [symbol for symbol in config.rule.symbols if symbol in panel.symbols]
        if rule_symbols:
            symbols.update(rule_symbols)
            frame = _base_frame(panel, rule_symbols)
            specs = build_generated_rule_specs(config.rule)
            for spec in specs:
                frame[spec.name] = _compute_rule_values(frame, spec)
            frames.append(frame.set_index(["date", "symbol"]).sort_index())
            catalogs.append(
                pd.DataFrame(
                    [
                        {
                            "name": spec.name,
                            "generator_line": spec.generator_line,
                            "family": spec.rule_family,
                            "predictor_type": spec.predictor_type,
                            "alpha_direction_policy": spec.alpha_direction_policy,
                            "score_method_family": np.nan,
                            "descriptor_id": np.nan,
                            "transform_id": np.nan,
                            "horizon_id": np.nan,
                            "horizon_group": spec.horizon_group,
                            "native_window": spec.native_window,
                            "mapped_window_4h": spec.mapped_window_4h,
                            "mapping_method": spec.mapping_method,
                            "threshold_bps": spec.threshold_bps,
                            "short_window": spec.short_window,
                            "long_window": spec.long_window,
                        }
                        for spec in specs
                    ]
                )
            )

    if not frames:
        raise ValueError("No generator line produced any symbols.")

    combined = pd.concat(frames, axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()].sort_index()
    catalog = pd.concat(catalogs, ignore_index=True).sort_values(["generator_line", "family", "name"]).reset_index(drop=True)
    primary_horizon = config.descriptor.primary_horizon if line == "descriptor" else config.rule.primary_horizon if line == "rule" else max(config.descriptor.primary_horizon, config.rule.primary_horizon)
    summary = _raw_summary(catalog, combined, primary_horizon)
    return {
        "symbols": sorted(symbols),
        "catalog": catalog,
        "raw_frame": combined,
        "raw_summary": summary,
    }


def write_raw_artifacts(result: dict[str, pd.DataFrame | list[str]], output_dir: str | Path) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    catalog = result["catalog"]
    summary = result["raw_summary"]
    assert isinstance(catalog, pd.DataFrame)
    assert isinstance(summary, pd.DataFrame)
    catalog.to_csv(target / "generated_raw_predictor_catalog.csv", index=False)
    summary.to_csv(target / "generated_raw_predictor_summary.csv", index=False)
