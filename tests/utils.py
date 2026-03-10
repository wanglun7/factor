from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import RunConfig, TSBacktestConfig, TSResearchConfig, TSUniverseConfig, load_config
from data.cleaner import prepare
from data.fetcher import LocalCsvProvider, fetch


def make_csv_dataset(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    dates = pd.date_range("2021-01-01", periods=6 * 730, freq="4h")
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "ATOM"]
    sectors = {symbol: "core" for symbol in symbols}

    price_rows: list[dict[str, object]] = []
    spot_rows: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    meta_rows: list[dict[str, object]] = []
    funding_rows: list[dict[str, object]] = []

    for symbol_index, symbol in enumerate(symbols):
        listing_date = dates[0] - pd.Timedelta(days=300 + symbol_index)
        meta_rows.append({"symbol": symbol, "listing_date": listing_date, "sector": sectors[symbol]})
        close = 100.0 + symbol_index * 10.0
        for bar_index, date in enumerate(dates):
            trend_block = 0.0006 if (bar_index // 240) % 2 == 0 else -0.0002
            reversal_block = -0.8 if bar_index > 0 and ((bar_index + symbol_index) % 19 == 0) else 0.2
            drift = trend_block + reversal_block * 0.00025 + symbol_index * 0.00001
            close = close * (1.0 + drift)
            volume = 5_000_000 + symbol_index * 250_000 + 500 * bar_index
            open_ = close * 0.998
            high = close * 1.01
            low = close * 0.99
            price_rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "vwap": (open_ + close) / 2.0,
                    "exchange": "binance_perp",
                }
            )
            spot_close = close * 0.998
            spot_rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "open": spot_close * 0.998,
                    "high": spot_close * 1.01,
                    "low": spot_close * 0.99,
                    "close": spot_close,
                    "volume": volume * 0.9,
                    "vwap": spot_close,
                    "exchange": "binance_spot",
                }
            )
            index_close = close * 0.997
            index_rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "open": index_close,
                    "high": index_close,
                    "low": index_close,
                    "close": index_close,
                    "volume": volume,
                    "vwap": index_close,
                    "exchange": "index_price",
                }
            )
            if bar_index % 2 == 0:
                funding_rows.append(
                    {
                        "date": date,
                        "symbol": symbol,
                        "funding_rate": 0.00008 * np.sin((bar_index + symbol_index) / 18.0),
                    }
                )

    pd.DataFrame(price_rows).to_csv(root / "prices_4h_perp.csv", index=False)
    pd.DataFrame(spot_rows).to_csv(root / "spot_prices_4h.csv", index=False)
    pd.DataFrame(index_rows).to_csv(root / "index_prices_4h.csv", index=False)
    pd.DataFrame(meta_rows).to_csv(root / "universe_meta.csv", index=False)
    pd.DataFrame(funding_rows).to_csv(root / "funding_rates_8h.csv", index=False)


def make_panel(root: Path):
    config = make_config(root)
    provider = LocalCsvProvider(root=root, config=config.data)
    bundle = fetch(start=config.data.start_date, end=config.data.end_date, provider=provider)
    return prepare(bundle)


def make_config(root: Path) -> RunConfig:
    config = load_config("config/settings.yaml")
    return RunConfig(
        data=type(config.data)(
            provider=config.data.provider,
            csv_dir=str(root),
            start_date=config.data.start_date,
            end_date="2022-12-31",
            bar_interval=config.data.bar_interval,
            price_basis=config.data.price_basis,
            price_file=config.data.price_file,
            spot_price_file=config.data.spot_price_file,
            index_price_file=config.data.index_price_file,
            funding_file=config.data.funding_file,
            open_interest_file=config.data.open_interest_file,
        ),
        ts_universe=TSUniverseConfig(symbols=config.ts_universe.symbols),
        ts_research=TSResearchConfig(
            horizons=config.ts_research.horizons,
            primary_horizon=config.ts_research.primary_horizon,
            signal_z_window=360,
            signal_z_min_periods=120,
            entry_z=config.ts_research.entry_z,
            exit_z=config.ts_research.exit_z,
            one_way_cost_bps=config.ts_research.one_way_cost_bps,
            output_dir=config.ts_research.output_dir,
            min_history_bars=180,
            annualization=config.ts_research.annualization,
            bars_per_day=config.ts_research.bars_per_day,
        ),
        ts_backtest=TSBacktestConfig(
            benchmark_symbol=config.ts_backtest.benchmark_symbol,
            output_dir=config.ts_backtest.output_dir,
            risk_weight_vol_window=config.ts_backtest.risk_weight_vol_window,
        ),
        raw_predictors=type(config.raw_predictors)(
            output_dir=config.raw_predictors.output_dir,
            horizons=config.raw_predictors.horizons,
            primary_horizon=config.raw_predictors.primary_horizon,
            bars_per_day=config.raw_predictors.bars_per_day,
            annualization=config.raw_predictors.annualization,
        ),
        standardized_scores=type(config.standardized_scores)(
            output_dir=config.standardized_scores.output_dir,
            horizons=config.standardized_scores.horizons,
            primary_horizon=config.standardized_scores.primary_horizon,
            z_window=360,
            z_min_periods=120,
            winsor_clip_z=config.standardized_scores.winsor_clip_z,
            clip_quantile=config.standardized_scores.clip_quantile,
            ewm_span=360,
            rule_spread_gate=config.standardized_scores.rule_spread_gate,
            continuous_strong_spread_gate=config.standardized_scores.continuous_strong_spread_gate,
            continuous_conditional_spread_gate=config.standardized_scores.continuous_conditional_spread_gate,
            continuous_conditional_monotonicity_gate=config.standardized_scores.continuous_conditional_monotonicity_gate,
        ),
        continuous_score_experiment=type(config.continuous_score_experiment)(
            output_dir=config.continuous_score_experiment.output_dir,
            horizons=config.continuous_score_experiment.horizons,
            primary_horizon=config.continuous_score_experiment.primary_horizon,
            window=360,
            min_periods=120,
            clip_quantile=config.continuous_score_experiment.clip_quantile,
            ewm_span=360,
        ),
    )
