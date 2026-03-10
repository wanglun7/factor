from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app_config import RawPredictorConfig, TSUniverseConfig
from models import AlignedPanel


@dataclass(frozen=True, slots=True)
class RawPredictorSpec:
    name: str
    family: str
    predictor_type: str
    readiness: str
    source_level: str
    native_definition: str
    native_window: str
    mapped_window_4h: int | None
    required_inputs: tuple[str, ...]
    alpha_direction: str
    citations: tuple[str, ...]
    notes: str


def _days_to_bars(days: int) -> int:
    return days * 6


def _weeks_to_bars(weeks: int) -> int:
    return weeks * 7 * 6


def _catalog() -> list[RawPredictorSpec]:
    specs: list[RawPredictorSpec] = []
    for days in (20, 50, 100, 150, 200):
        specs.append(
            RawPredictorSpec(
                name=f"vma_{days}d",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Current log price above trailing n-day moving average of log prices.",
                native_window=f"{days}d",
                mapped_window_4h=_days_to_bars(days),
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("technical_trading_rules_crypto_market",),
                notes="Buy when current log price exceeds trailing n-day log-price average; otherwise flat.",
            )
        )
    for days in (50, 150, 200):
        specs.append(
            RawPredictorSpec(
                name=f"trb_{days}d",
                family="price_trend",
                predictor_type="ternary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Break above prior n-day resistance or below prior n-day support.",
                native_window=f"{days}d",
                mapped_window_4h=_days_to_bars(days),
                required_inputs=("close",),
                alpha_direction="positive_on_up_break_negative_on_down_break",
                citations=("profitability_bitcoin_technical_rules",),
                notes="Uses prior rolling support/resistance from the previous n days.",
            )
        )
    specs.extend(
        [
            RawPredictorSpec(
                name="prev_day_return",
                family="reversal_mean_reversion",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Previous 1-day return.",
                native_window="1d",
                mapped_window_4h=_days_to_bars(1),
                required_inputs=("close",),
                alpha_direction="lower_is_more_positive_future_return",
                citations=("short_term_reversal_crypto", "ml_crypto_lagged_return"),
                notes="Stored as raw previous-day return; reversal interpretation lives in metadata.",
            ),
            RawPredictorSpec(
                name="amihud_20w",
                family="volatility_liquidity",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="20-week Amihud illiquidity measure.",
                native_window="20w",
                mapped_window_4h=_weeks_to_bars(20),
                required_inputs=("close", "volume"),
                alpha_direction="lower_is_more_liquid",
                citations=("liquidity_risk_expected_crypto_returns",),
                notes="Rolling mean of absolute return over dollar volume.",
            ),
            RawPredictorSpec(
                name="funding_rate_level",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Latest realized funding rate aligned to the bar.",
                native_window="8h",
                mapped_window_4h=2,
                required_inputs=("funding_rate_8h",),
                alpha_direction="sign_preserved",
                citations=("eth_price_funding_rates", "coinmetrics_funding_docs"),
                notes="Uses the latest realized funding observation available at the bar.",
            ),
            RawPredictorSpec(
                name="lagged_funding_rate_1",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Previous realized funding rate.",
                native_window="8h",
                mapped_window_4h=2,
                required_inputs=("funding_rate_lag1",),
                alpha_direction="sign_preserved",
                citations=("eth_price_funding_rates",),
                notes="Uses the prior funding observation as a lagged funding predictor.",
            ),
            RawPredictorSpec(
                name="premium",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Premium term from perpetual funding rules using perp and index prices.",
                native_window="instantaneous",
                mapped_window_4h=1,
                required_inputs=("close", "index_close"),
                alpha_direction="higher_is_more_premium_positive",
                citations=("coinbase_funding_rules",),
                notes="Computed as price premium over index, normalized by 24h convention from exchange rules.",
            ),
            RawPredictorSpec(
                name="funding_basis_rate",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Latest funding rate scaled by time remaining to the next settlement.",
                native_window="8h",
                mapped_window_4h=2,
                required_inputs=("funding_rate_8h",),
                alpha_direction="sign_preserved",
                citations=("futures_help_center_funding_rate",),
                notes="Implements the funding-basis-rate definition from perpetual futures documentation.",
            ),
            RawPredictorSpec(
                name="relative_basis",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Relative futures-spot basis.",
                native_window="instantaneous",
                mapped_window_4h=1,
                required_inputs=("close", "spot_close"),
                alpha_direction="higher_is_more_basis_positive",
                citations=("anatomy_perpetual_futures_returns", "coinmetrics_api_docs"),
                notes="Computed from paired perp and spot prices at the same timestamp.",
            ),
            RawPredictorSpec(
                name="log_basis",
                family="derivatives_carry_funding",
                predictor_type="continuous",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Log futures-spot basis.",
                native_window="instantaneous",
                mapped_window_4h=1,
                required_inputs=("close", "spot_close"),
                alpha_direction="higher_is_more_basis_positive",
                citations=("anatomy_perpetual_futures_returns",),
                notes="Log basis between perp and spot prices.",
            ),
        ]
    )
    specs.extend(
        [
            RawPredictorSpec(
                name="sma_price_crossover_12",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing SMA with window 12.",
                native_window="12",
                mapped_window_4h=12,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-SMA crossover with literature-backed 12-bar window example.",
            ),
            RawPredictorSpec(
                name="sma_price_crossover_24",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing SMA with window 24.",
                native_window="24",
                mapped_window_4h=24,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-SMA crossover with literature-backed 24-bar window example.",
            ),
            RawPredictorSpec(
                name="sma_price_crossover_72",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing SMA with window 72.",
                native_window="72",
                mapped_window_4h=72,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-SMA crossover with literature-backed 72-bar window example.",
            ),
            RawPredictorSpec(
                name="ema_price_crossover_12",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing EMA with window 12.",
                native_window="12",
                mapped_window_4h=12,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-EMA crossover with literature-backed 12-bar window example.",
            ),
            RawPredictorSpec(
                name="ema_price_crossover_24",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing EMA with window 24.",
                native_window="24",
                mapped_window_4h=24,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-EMA crossover with literature-backed 24-bar window example.",
            ),
            RawPredictorSpec(
                name="ema_price_crossover_72",
                family="price_trend",
                predictor_type="binary_rule",
                readiness="implementable",
                source_level="formula_level",
                native_definition="Price crossing EMA with window 72.",
                native_window="72",
                mapped_window_4h=72,
                required_inputs=("close",),
                alpha_direction="higher_is_more_trend_positive",
                citations=("bitcoin_technical_analysis_mdpi",),
                notes="Binary price-vs-EMA crossover with literature-backed 72-bar window example.",
            ),
        ]
    )
    return specs


def _eligible_symbols(panel: AlignedPanel, universe_config: TSUniverseConfig) -> list[str]:
    available = set(panel.symbols)
    return [symbol for symbol in universe_config.symbols if symbol in available]


def _settlement_fraction(index: pd.DatetimeIndex) -> pd.Series:
    dates = pd.DatetimeIndex(index)
    hours_remaining = 8 - (dates.hour % 8)
    hours_remaining = np.where(hours_remaining == 0, 8, hours_remaining)
    return pd.Series(hours_remaining / 8.0, index=index, dtype=float)


def _build_predictor_frame(panel: AlignedPanel, symbols: list[str]) -> pd.DataFrame:
    frame = panel.frame.reset_index()
    frame = frame.loc[frame["symbol"].isin(symbols)].copy()
    frame = frame.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = frame.groupby("symbol", group_keys=False)
    frame["log_close"] = np.log(frame["close"])
    frame["prev_day_return"] = frame["close"] / grouped["close"].shift(6) - 1.0
    perp_return = grouped["close"].pct_change(fill_method=None).abs()
    amihud_point = perp_return / (frame["close"] * frame["volume"]).replace(0.0, np.nan)
    frame["amihud_20w"] = amihud_point.groupby(frame["symbol"]).transform(
        lambda values: values.rolling(_weeks_to_bars(20), min_periods=_weeks_to_bars(20)).mean()
    )
    frame["funding_rate_level"] = frame["funding_rate_8h"]
    frame["lagged_funding_rate_1"] = frame["funding_rate_lag1"]
    frame["premium"] = (frame["close"] - frame["index_close"]) / frame["index_close"].replace(0.0, np.nan) / 24.0
    frame["funding_basis_rate"] = frame["funding_rate_level"] * _settlement_fraction(pd.DatetimeIndex(frame["date"])).to_numpy()
    frame["relative_basis"] = (frame["close"] - frame["spot_close"]) / frame["spot_close"].replace(0.0, np.nan)
    frame["log_basis"] = np.log(frame["close"] / frame["spot_close"])
    for bars in (12, 24, 72):
        sma = grouped["close"].transform(lambda values: values.shift(1).rolling(bars, min_periods=bars).mean())
        frame[f"sma_price_crossover_{bars}"] = np.where(frame["close"] > sma, 1.0, 0.0)
        ema = grouped["close"].transform(lambda values: values.shift(1).ewm(span=bars, adjust=False, min_periods=bars).mean())
        frame[f"ema_price_crossover_{bars}"] = np.where(frame["close"] > ema, 1.0, 0.0)

    for days in (20, 50, 100, 150, 200):
        window = _days_to_bars(days)
        trailing_ma = grouped["log_close"].transform(lambda values: values.shift(1).rolling(window, min_periods=window).mean())
        frame[f"vma_{days}d"] = np.where(frame["log_close"] > trailing_ma, 1.0, 0.0)
    for days in (50, 150, 200):
        window = _days_to_bars(days)
        resistance = grouped["close"].transform(lambda values: values.shift(1).rolling(window, min_periods=window).max())
        support = grouped["close"].transform(lambda values: values.shift(1).rolling(window, min_periods=window).min())
        signal = np.where(frame["close"] > resistance, 1.0, np.where(frame["close"] < support, -1.0, 0.0))
        frame[f"trb_{days}d"] = signal
    return frame


def _forward_return(frame: pd.DataFrame, horizon: int, delay: int) -> pd.Series:
    close = frame.pivot(index="date", columns="symbol", values="close").sort_index()
    forward = close.shift(-(horizon + delay)) / close.shift(-delay) - 1.0
    try:
        series = forward.stack(future_stack=True)
    except TypeError:
        series = forward.stack(dropna=False)
    series.name = f"forward_{horizon}bar_delay_{delay}"
    return series


def _spread_for_predictor(values: pd.Series, forward_returns: pd.Series, predictor_type: str) -> float:
    aligned = pd.concat([values.rename("value"), forward_returns.rename("forward")], axis=1).dropna()
    if aligned.empty:
        return 0.0
    if predictor_type == "continuous":
        ranked = aligned["value"].rank(method="first")
        try:
            buckets = pd.qcut(ranked, 5, labels=False, duplicates="drop")
        except ValueError:
            return 0.0
        aligned["bucket"] = buckets
        if aligned["bucket"].nunique() < 2:
            return 0.0
        grouped = aligned.groupby("bucket")["forward"].mean()
        return float(grouped.max() - grouped.min())
    values_unique = sorted(set(aligned["value"].dropna().tolist()))
    if predictor_type == "binary_rule":
        if not {0.0, 1.0}.issubset(set(values_unique)):
            if {-1.0, 1.0}.issubset(set(values_unique)):
                return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == -1.0, "forward"].mean())
            return 0.0
        return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == 0.0, "forward"].mean())
    if predictor_type == "ternary_rule":
        if {1.0, -1.0}.issubset(set(values_unique)):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == -1.0, "forward"].mean())
        if {1.0, 0.0}.issubset(set(values_unique)):
            return float(aligned.loc[aligned["value"] == 1.0, "forward"].mean() - aligned.loc[aligned["value"] == 0.0, "forward"].mean())
    return 0.0


def _catalog_frame(specs: list[RawPredictorSpec]) -> pd.DataFrame:
    rows = [
        {
            "name": spec.name,
            "family": spec.family,
            "predictor_type": spec.predictor_type,
            "readiness": spec.readiness,
            "source_level": spec.source_level,
            "native_definition": spec.native_definition,
            "native_window": spec.native_window,
            "mapped_window_4h": spec.mapped_window_4h,
            "required_inputs": "|".join(spec.required_inputs),
            "alpha_direction": spec.alpha_direction,
            "citations": "|".join(spec.citations),
            "notes": spec.notes,
        }
        for spec in specs
    ]
    return pd.DataFrame(rows).sort_values(["readiness", "family", "name"]).reset_index(drop=True)


def _evidence_markdown(specs: list[RawPredictorSpec]) -> str:
    lines = ["# Raw Predictor Evidence", ""]
    for readiness in ("implementable", "candidate"):
        lines.append(f"## {readiness.title()}")
        for spec in [item for item in specs if item.readiness == readiness]:
            lines.append(f"- `{spec.name}` ({spec.family}, {spec.source_level})")
            lines.append(f"  - definition: {spec.native_definition}")
            lines.append(f"  - citations: {', '.join(spec.citations)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_raw_predictor_data_4h(panel: AlignedPanel, universe_config: TSUniverseConfig) -> dict[str, object]:
    symbols = _eligible_symbols(panel, universe_config)
    if not symbols:
        raise ValueError("No requested symbols are available in the aligned panel.")
    working = panel.frame.loc[panel.frame.index.get_level_values("symbol").isin(symbols)]
    missing: list[str] = []
    if working["spot_close"].notna().sum() == 0:
        missing.append("spot_prices_4h")
    if working["index_close"].notna().sum() == 0:
        missing.append("index_prices_4h")
    if working["funding_rate_8h"].notna().sum() == 0:
        missing.append("funding_rates_8h")
    if missing:
        raise ValueError(f"Missing required raw predictor inputs: {missing}")
    return {"status": "ok", "symbols": symbols, "required_inputs": ["perp_ohlcv", "spot_prices_4h", "index_prices_4h", "funding_rates_8h"]}


def run_raw_predictor_research_4h(
    panel: AlignedPanel,
    universe_config: TSUniverseConfig,
    config: RawPredictorConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    specs = _catalog()
    symbols = _eligible_symbols(panel, universe_config)
    validate_raw_predictor_data_4h(panel, universe_config)
    factor_frame = _build_predictor_frame(panel, symbols).set_index(["date", "symbol"]).sort_index()

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    catalog = _catalog_frame(specs)
    mapping = catalog.loc[:, ["name", "native_window", "mapped_window_4h", "predictor_type", "readiness", "source_level"]].copy()

    implementable = [spec for spec in specs if spec.readiness == "implementable"]
    coverage_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for spec in implementable:
        values = factor_frame[spec.name]
        coverage = float(values.notna().mean()) if len(values) else 0.0
        coverage_rows.append(
            {
                "name": spec.name,
                "family": spec.family,
                "coverage_ratio": coverage,
                "non_null_observations": int(values.notna().sum()),
            }
        )
        primary_spread = _spread_for_predictor(values, _forward_return(factor_frame.reset_index(), config.primary_horizon, 0), spec.predictor_type)
        delay_1_spread = _spread_for_predictor(values, _forward_return(factor_frame.reset_index(), config.primary_horizon, 1), spec.predictor_type)
        delay_2_spread = _spread_for_predictor(values, _forward_return(factor_frame.reset_index(), config.primary_horizon, 2), spec.predictor_type)
        summary_rows.append(
            {
                "name": spec.name,
                "family": spec.family,
                "predictor_type": spec.predictor_type,
                "coverage_ratio": coverage,
                "primary_horizon": config.primary_horizon,
                "delay_0_spread": primary_spread,
                "delay_1_spread": delay_1_spread,
                "delay_2_spread": delay_2_spread,
                "source_level": spec.source_level,
            }
        )

    catalog.to_csv(target / "raw_predictor_catalog.csv", index=False)
    pd.DataFrame(coverage_rows).sort_values(["family", "name"]).to_csv(target / "raw_predictor_coverage.csv", index=False)
    pd.DataFrame(summary_rows).sort_values(["family", "name"]).to_csv(target / "raw_predictor_summary.csv", index=False)
    mapping.to_csv(target / "raw_predictor_mapping_4h.csv", index=False)
    (target / "raw_predictor_evidence.md").write_text(_evidence_markdown(specs), encoding="utf-8")

    return {
        "state": "complete",
        "implementable_predictors": [spec.name for spec in implementable],
        "candidate_predictors": [spec.name for spec in specs if spec.readiness == "candidate"],
        "artifacts": {
            "catalog": "raw_predictor_catalog.csv",
            "coverage": "raw_predictor_coverage.csv",
            "summary": "raw_predictor_summary.csv",
            "mapping": "raw_predictor_mapping_4h.csv",
            "evidence": "raw_predictor_evidence.md",
        },
    }
