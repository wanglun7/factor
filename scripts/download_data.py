from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd


START_DATE = "2021-01-01"
END_DATE = "2024-12-31"
OUT_DIR = Path(__file__).parent.parent / "local_data"

COINS: dict[str, dict[str, str]] = {
    "BTC": {"sector": "l1", "listing_date": "2017-07-01"},
    "ETH": {"sector": "l1", "listing_date": "2017-08-01"},
    "SOL": {"sector": "l1", "listing_date": "2020-04-10"},
    "BNB": {"sector": "exchange", "listing_date": "2017-10-01"},
    "XRP": {"sector": "payment", "listing_date": "2018-05-01"},
    "ADA": {"sector": "l1", "listing_date": "2018-04-17"},
    "DOGE": {"sector": "meme", "listing_date": "2019-07-05"},
    "AVAX": {"sector": "l1", "listing_date": "2020-09-23"},
    "LINK": {"sector": "infra", "listing_date": "2019-01-16"},
    "DOT": {"sector": "l1", "listing_date": "2020-08-19"},
    "LTC": {"sector": "payment", "listing_date": "2017-12-13"},
    "BCH": {"sector": "payment", "listing_date": "2018-01-12"},
    "ATOM": {"sector": "l1", "listing_date": "2019-03-14"},
    "NEAR": {"sector": "l1", "listing_date": "2020-10-16"},
    "MATIC": {"sector": "l2", "listing_date": "2019-04-26"},
    "UNI": {"sector": "defi", "listing_date": "2020-09-17"},
    "AAVE": {"sector": "defi", "listing_date": "2020-10-16"},
    "FIL": {"sector": "infra", "listing_date": "2020-10-15"},
    "TRX": {"sector": "l1", "listing_date": "2018-06-11"},
    "XLM": {"sector": "payment", "listing_date": "2018-06-11"},
    "ALGO": {"sector": "l1", "listing_date": "2019-06-26"},
    "VET": {"sector": "l1", "listing_date": "2019-06-01"},
    "SAND": {"sector": "gaming", "listing_date": "2020-08-14"},
    "MANA": {"sector": "gaming", "listing_date": "2019-10-31"},
    "CRV": {"sector": "defi", "listing_date": "2020-08-14"},
    "LDO": {"sector": "defi", "listing_date": "2022-03-10"},
    "OP": {"sector": "l2", "listing_date": "2022-05-31"},
    "ARB": {"sector": "l2", "listing_date": "2023-03-23"},
    "APT": {"sector": "l1", "listing_date": "2022-10-19"},
    "ICP": {"sector": "l1", "listing_date": "2021-05-10"},
}


def _ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_prices() -> pd.DataFrame:
    exchange = ccxt.binance({"options": {"defaultType": "spot"}})
    exchange.load_markets()
    since_ms = _ts_ms(START_DATE)
    end_ms = _ts_ms("2025-01-01")
    rows: list[dict[str, object]] = []

    for symbol in COINS:
        market = f"{symbol}/USDT"
        if market not in exchange.markets:
            print(f"[warn] missing spot market for {symbol}, skipping")
            continue

        cursor = since_ms
        while cursor < end_ms:
            candles = exchange.fetch_ohlcv(market, timeframe="1d", since=cursor, limit=1000)
            if not candles:
                break
            for ts, open_, high, low, close, volume in candles:
                date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                if START_DATE <= date <= END_DATE:
                    rows.append(
                        {
                            "date": date,
                            "symbol": symbol,
                            "open": open_,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                            "vwap": (high + low + close) / 3.0,
                            "exchange": "binance",
                        }
                    )
            last_ts = candles[-1][0]
            if last_ts >= end_ms or len(candles) < 1000:
                break
            cursor = last_ts + 86_400_000
            time.sleep(0.2)

    frame = pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)
    return frame


def build_universe_meta() -> pd.DataFrame:
    return pd.DataFrame(
        [{"symbol": symbol, "listing_date": meta["listing_date"], "sector": meta["sector"]} for symbol, meta in COINS.items()]
    ).sort_values("symbol")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download minimal market data for the research prototype")
    parser.add_argument("--only", choices=["prices", "meta"], default=None)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    if args.only in (None, "prices"):
        prices = fetch_prices()
        prices.to_csv(OUT_DIR / "prices.csv", index=False)
        outputs["prices"] = str(OUT_DIR / "prices.csv")

    if args.only in (None, "meta"):
        meta = build_universe_meta()
        meta.to_csv(OUT_DIR / "universe_meta.csv", index=False)
        outputs["meta"] = str(OUT_DIR / "universe_meta.csv")

    print(json.dumps({"state": "complete", "outputs": outputs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
