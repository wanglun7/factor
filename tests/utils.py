from __future__ import annotations

from pathlib import Path

import pandas as pd

from app_config import RunConfig, load_config
from backtest.engine import run_backtest
from data.cleaner import prepare
from data.fetcher import LocalCsvProvider, fetch
from strategy import MomentumReversalSignal


def make_csv_dataset(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    dates = pd.date_range("2021-01-01", periods=220, freq="D")
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "UNI", "AAVE"]
    sectors = {
        "BTC": "store",
        "ETH": "smart_contract",
        "SOL": "smart_contract",
        "BNB": "exchange",
        "XRP": "payments",
        "ADA": "smart_contract",
        "DOGE": "meme",
        "AVAX": "smart_contract",
        "LINK": "oracle",
        "DOT": "interoperability",
        "UNI": "defi",
        "AAVE": "defi",
    }
    shock_map = {"SOL": -0.12, "ADA": 0.10, "DOGE": -0.08, "XRP": 0.06}
    price_rows = []
    meta_rows = []
    for symbol_index, symbol in enumerate(symbols):
        base_price = 50 + symbol_index * 10
        listing_date = dates[0] - pd.Timedelta(days=220 + symbol_index)
        meta_rows.append({"symbol": symbol, "listing_date": listing_date, "sector": sectors[symbol]})
        for day_index, date in enumerate(dates):
            trend = 1 + (0.0012 + symbol_index * 0.00012) * day_index
            seasonality = 1 + 0.015 * ((day_index + symbol_index) % 10) / 10
            close = base_price * trend * seasonality
            if day_index >= len(dates) - 3:
                close *= 1 + shock_map.get(symbol, 0.0) * (day_index - (len(dates) - 4)) / 3
            open_ = close * 0.995
            high = close * 1.01
            low = close * 0.99
            volume = 3_000_000 - symbol_index * 120_000 + day_index * 1_500
            price_rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "vwap": (open_ + close) / 2,
                    "exchange": "binance",
                }
            )
    pd.DataFrame(price_rows).to_csv(root / "prices.csv", index=False)
    pd.DataFrame(meta_rows).to_csv(root / "universe_meta.csv", index=False)


def make_panel(root: Path):
    provider = LocalCsvProvider(root=root)
    bundle = fetch(start="2021-01-01", end="2021-08-31", provider=provider)
    return prepare(bundle)


def make_config(root: Path) -> RunConfig:
    config = load_config("config/settings.yaml")
    return RunConfig(
        data=type(config.data)(
            provider=config.data.provider,
            csv_dir=str(root),
            start_date=config.data.start_date,
            end_date=config.data.end_date,
        ),
        universe=config.universe,
        strategy=config.strategy,
        portfolio=config.portfolio,
        backtest=config.backtest,
    )


def make_backtest_result(root: Path):
    config = make_config(root)
    panel = make_panel(root)
    signal = MomentumReversalSignal.from_config(config.strategy)
    return run_backtest(
        panel=panel,
        signal=signal,
        universe_config=config.universe,
        portfolio_config=config.portfolio,
        backtest_config=config.backtest,
    )
