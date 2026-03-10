from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import ccxt
import pandas as pd
import requests
import yfinance as yf


START_DATE = "2021-01-01"
END_DATE = "2024-12-31"
OUT_DIR = Path(__file__).parent.parent / "local_data"
CORE_SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "ATOM"]

COINS: dict[str, dict[str, str]] = {
    "BTC": {"cg_id": "bitcoin", "llama_slug": "ethereum", "sector": "l1", "listing_date": "2017-07-01"},
    "ETH": {"cg_id": "ethereum", "llama_slug": "ethereum", "sector": "l1", "listing_date": "2017-08-01"},
    "SOL": {"cg_id": "solana", "llama_slug": "solana", "sector": "l1", "listing_date": "2020-04-10"},
    "BNB": {"cg_id": "binancecoin", "llama_slug": "bsc", "sector": "exchange", "listing_date": "2017-10-01"},
    "XRP": {"cg_id": "ripple", "llama_slug": "", "sector": "payment", "listing_date": "2018-05-01"},
    "ADA": {"cg_id": "cardano", "llama_slug": "cardano", "sector": "l1", "listing_date": "2018-04-17"},
    "DOGE": {"cg_id": "dogecoin", "llama_slug": "", "sector": "meme", "listing_date": "2019-07-05"},
    "AVAX": {"cg_id": "avalanche-2", "llama_slug": "avalanche", "sector": "l1", "listing_date": "2020-09-23"},
    "LINK": {"cg_id": "chainlink", "llama_slug": "", "sector": "infra", "listing_date": "2019-01-16"},
    "DOT": {"cg_id": "polkadot", "llama_slug": "", "sector": "l1", "listing_date": "2020-08-19"},
    "LTC": {"cg_id": "litecoin", "llama_slug": "", "sector": "payment", "listing_date": "2017-12-13"},
    "BCH": {"cg_id": "bitcoin-cash", "llama_slug": "", "sector": "payment", "listing_date": "2018-01-12"},
    "ATOM": {"cg_id": "cosmos", "llama_slug": "cosmoshub", "sector": "l1", "listing_date": "2019-03-14"},
    "NEAR": {"cg_id": "near", "llama_slug": "near", "sector": "l1", "listing_date": "2020-10-16"},
    "MATIC": {"cg_id": "matic-network", "llama_slug": "polygon", "sector": "l2", "listing_date": "2019-04-26"},
    "UNI": {"cg_id": "uniswap", "llama_slug": "uniswap", "sector": "defi", "listing_date": "2020-09-17"},
    "AAVE": {"cg_id": "aave", "llama_slug": "aave", "sector": "defi", "listing_date": "2020-10-16"},
    "FIL": {"cg_id": "filecoin", "llama_slug": "", "sector": "infra", "listing_date": "2020-10-15"},
    "TRX": {"cg_id": "tron", "llama_slug": "tron", "sector": "l1", "listing_date": "2018-06-11"},
    "XLM": {"cg_id": "stellar", "llama_slug": "", "sector": "payment", "listing_date": "2018-06-11"},
    "ALGO": {"cg_id": "algorand", "llama_slug": "algorand", "sector": "l1", "listing_date": "2019-06-26"},
    "VET": {"cg_id": "vechain", "llama_slug": "", "sector": "l1", "listing_date": "2019-06-01"},
    "SAND": {"cg_id": "the-sandbox", "llama_slug": "", "sector": "gaming", "listing_date": "2020-08-14"},
    "MANA": {"cg_id": "decentraland", "llama_slug": "", "sector": "gaming", "listing_date": "2019-10-31"},
    "CRV": {"cg_id": "curve-dao-token", "llama_slug": "curve", "sector": "defi", "listing_date": "2020-08-14"},
    "LDO": {"cg_id": "lido-dao", "llama_slug": "lido", "sector": "defi", "listing_date": "2022-03-10"},
    "OP": {"cg_id": "optimism", "llama_slug": "optimism", "sector": "l2", "listing_date": "2022-05-31"},
    "ARB": {"cg_id": "arbitrum", "llama_slug": "arbitrum", "sector": "l2", "listing_date": "2023-03-23"},
    "APT": {"cg_id": "aptos", "llama_slug": "aptos", "sector": "l1", "listing_date": "2022-10-19"},
    "ICP": {"cg_id": "internet-computer", "llama_slug": "", "sector": "l1", "listing_date": "2021-05-10"},
}


def _ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _date_range() -> pd.DatetimeIndex:
    return pd.date_range(START_DATE, END_DATE, freq="D")


def _candidate_markets(symbol: str, exchange_name: str) -> list[str]:
    if exchange_name == "okx":
        return [f"{symbol}/USDT:USDT", f"{symbol}-USDT-SWAP"]
    return [f"{symbol}/USDT:USDT"]


def _build_exchange(exchange_name: str):
    return getattr(ccxt, exchange_name)()


def fetch_prices() -> pd.DataFrame:
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()
    since_ms = _ts_ms(START_DATE)
    end_ms = _ts_ms("2025-01-01")
    rows: list[dict[str, object]] = []
    for symbol in CORE_SYMBOLS:
        market = f"{symbol}/USDT:USDT"
        if market not in exchange.markets:
            continue
        cursor = since_ms
        while cursor < end_ms:
            candles = exchange.fetch_ohlcv(market, timeframe="4h", since=cursor, limit=1000)
            if not candles:
                break
            for ts, open_, high, low, close, volume in candles:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                date = dt.strftime("%Y-%m-%d %H:%M:%S")
                if _ts_ms(START_DATE) <= ts < end_ms:
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
                            "exchange": "binance_perp",
                        }
                    )
            last_ts = candles[-1][0]
            if last_ts >= end_ms or len(candles) < 1000:
                break
            cursor = last_ts + 14_400_000
            time.sleep(0.2)
    return pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_spot_prices() -> pd.DataFrame:
    exchange = ccxt.binance()
    exchange.load_markets()
    since_ms = _ts_ms(START_DATE)
    end_ms = _ts_ms("2025-01-01")
    rows: list[dict[str, object]] = []
    for symbol in CORE_SYMBOLS:
        market = f"{symbol}/USDT"
        if market not in exchange.markets:
            continue
        cursor = since_ms
        while cursor < end_ms:
            candles = exchange.fetch_ohlcv(market, timeframe="4h", since=cursor, limit=1000)
            if not candles:
                break
            for ts, open_, high, low, close, volume in candles:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                date = dt.strftime("%Y-%m-%d %H:%M:%S")
                if _ts_ms(START_DATE) <= ts < end_ms:
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
                            "exchange": "binance_spot",
                        }
                    )
            last_ts = candles[-1][0]
            if last_ts >= end_ms or len(candles) < 1000:
                break
            cursor = last_ts + 14_400_000
            time.sleep(0.2)
    return pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_index_prices() -> pd.DataFrame:
    start_ms = _ts_ms(START_DATE)
    end_ms = _ts_ms("2025-01-01")
    rows: list[dict[str, object]] = []
    session = requests.Session()
    for symbol in CORE_SYMBOLS:
        pair = f"{symbol}USDT"
        cursor = start_ms
        while cursor < end_ms:
            params = {
                "pair": pair,
                "interval": "4h",
                "limit": 1000,
                "startTime": cursor,
                "endTime": end_ms,
            }
            response = session.get("https://fapi.binance.com/fapi/v1/indexPriceKlines", params=params, timeout=30)
            response.raise_for_status()
            candles = response.json()
            if not candles:
                break
            for candle in candles:
                ts = int(candle[0])
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                date = dt.strftime("%Y-%m-%d %H:%M:%S")
                if start_ms <= ts < end_ms:
                    open_, high, low, close = map(float, candle[1:5])
                    rows.append(
                        {
                            "date": date,
                            "symbol": symbol,
                            "open": open_,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": 0.0,
                            "vwap": close,
                            "exchange": "binance_index",
                        }
                    )
            last_ts = int(candles[-1][0])
            if last_ts >= end_ms or len(candles) < 1000:
                break
            cursor = last_ts + 14_400_000
            time.sleep(0.2)
    return pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_funding_rates() -> pd.DataFrame:
    since_ms = _ts_ms(START_DATE)
    end_ms = _ts_ms("2025-01-01")
    rows: list[dict[str, object]] = []
    exchanges = [
        ("binance", ccxt.binance({"options": {"defaultType": "future"}})),
        ("bybit", _build_exchange("bybit")),
        ("okx", _build_exchange("okx")),
    ]
    for _, exchange in exchanges:
        exchange.load_markets()
    for symbol in CORE_SYMBOLS:
        all_records: list[dict[str, object]] = []
        for exchange_name, exchange in exchanges:
            markets = [m for m in _candidate_markets(symbol, exchange_name) if m in exchange.markets]
            if not markets:
                continue
            market = markets[0]
            cursor = since_ms
            try:
                while cursor < end_ms:
                    records = exchange.fetch_funding_rate_history(market, since=cursor, limit=1000)
                    if not records:
                        break
                    for record in records:
                        ts = record.get("timestamp")
                        rate = record.get("fundingRate")
                        if ts is None or rate is None:
                            continue
                        date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        all_records.append({"date": date, "symbol": symbol, "funding_rate": rate})
                    last_ts = records[-1]["timestamp"]
                    if last_ts >= end_ms or len(records) < 1000:
                        break
                    cursor = last_ts + 1
                    time.sleep(0.1)
                if all_records:
                    break
            except Exception as exc:
                print(f"[warn] funding unavailable for {symbol} on {exchange_name}: {exc}")
                continue
        if all_records:
            rows.extend(pd.DataFrame(all_records).to_dict("records"))
    return pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_open_interest() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    exchanges = [
        ("bybit", _build_exchange("bybit")),
        ("okx", _build_exchange("okx")),
        ("binance", ccxt.binance({"options": {"defaultType": "future"}})),
    ]
    for _, exchange in exchanges:
        exchange.load_markets()
    for symbol in CORE_SYMBOLS:
        symbol_rows: list[dict[str, object]] = []
        for exchange_name, exchange in exchanges:
            markets = [m for m in _candidate_markets(symbol, exchange_name) if m in exchange.markets]
            if not markets:
                continue
            market = markets[0]
            try:
                history = exchange.fetch_open_interest_history(market, timeframe="1d", since=_ts_ms(START_DATE), limit=1000)
            except Exception as exc:
                print(f"[warn] oi unavailable for {symbol} on {exchange_name}: {exc}")
                history = []
            for record in history:
                ts = record.get("timestamp")
                oi = record.get("openInterestAmount") or record.get("openInterestValue")
                if ts is None or oi is None:
                    continue
                date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                if START_DATE <= date <= END_DATE:
                    symbol_rows.append({"date": date, "symbol": symbol, "open_interest": oi})
            if symbol_rows:
                break
        rows.extend(symbol_rows)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame({"date": [], "symbol": [], "open_interest": []})
    frame = frame.dropna(subset=["open_interest"]).sort_values(["symbol", "date"]).reset_index(drop=True)
    return frame


def fetch_market_caps() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for symbol, meta in COINS.items():
        url = f"https://api.coingecko.com/api/v3/coins/{meta['cg_id']}/market_chart?vs_currency=usd&days=max&interval=daily"
        try:
            payload = requests.get(url, timeout=30).json()
        except requests.RequestException as exc:
            print(f"[warn] market caps unavailable for {symbol}: {exc}")
            time.sleep(1.0)
            continue
        caps = payload.get("market_caps", [])
        for ts, market_cap in caps:
            date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if START_DATE <= date <= END_DATE:
                rows.append(
                    {
                        "date": date,
                        "symbol": symbol,
                        "market_cap": market_cap,
                        "circulating_supply": None,
                    }
                )
        time.sleep(1.0)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame({"date": [], "symbol": [], "market_cap": [], "circulating_supply": []})
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_tvl() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for symbol, meta in COINS.items():
        slug = meta["llama_slug"]
        if not slug:
            continue
        urls = [
            f"https://api.llama.fi/protocol/{slug}",
            f"https://api.llama.fi/charts/{slug}",
        ]
        payload = None
        for url in urls:
            try:
                with urlopen(url, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
                payload = None
        if payload is None:
            continue
        if isinstance(payload, dict) and "chainTvls" in payload:
            data = payload.get("chainTvls", {})
            if data:
                first = next(iter(data.values()))
                series = first.get("tvl", []) if isinstance(first, dict) else []
            else:
                series = []
        elif isinstance(payload, list):
            series = payload
        else:
            series = payload.get("tvl", []) if isinstance(payload, dict) else []
        for point in series:
            ts = point.get("date")
            tvl = point.get("totalLiquidityUSD")
            if ts is None or tvl is None:
                continue
            if isinstance(ts, str):
                try:
                    date = pd.to_datetime(ts).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            else:
                if ts > 10_000_000_000:
                    ts = ts / 1000
                date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            if START_DATE <= date <= END_DATE:
                rows.append({"date": date, "symbol": symbol, "tvl": tvl})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame({"date": [], "symbol": [], "tvl": []})
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def fetch_macro() -> pd.DataFrame:
    dxy = yf.download("DX-Y.NYB", start=START_DATE, end="2025-01-01", auto_adjust=False, progress=False)
    if dxy.empty:
        return pd.DataFrame(columns=["date", "dxy"])
    close_col = "Close" if "Close" in dxy.columns else dxy.columns[0]
    out = dxy[[close_col]].rename(columns={close_col: "dxy"}).reset_index()
    out["date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    return out[["date", "dxy"]]


def build_universe_meta() -> pd.DataFrame:
    return pd.DataFrame(
        [{"symbol": symbol, "listing_date": COINS[symbol]["listing_date"], "sector": COINS[symbol]["sector"]} for symbol in CORE_SYMBOLS]
    ).sort_values("symbol")


def build_data_manifest(outputs: dict[str, str]) -> dict[str, object]:
    manifest: dict[str, object] = {"start_date": START_DATE, "end_date": END_DATE, "outputs": outputs}
    dataset_specs = {
        "prices_4h_perp": ("prices_4h_perp.csv", "binance_perp"),
        "spot_prices_4h": ("spot_prices_4h.csv", "binance_spot"),
        "index_prices_4h": ("index_prices_4h.csv", "binance_index"),
    }
    for key, (filename, basis) in dataset_specs.items():
        path = OUT_DIR / filename
        if not path.exists():
            continue
        prices = pd.read_csv(path)
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
        manifest[key] = {
            "rows": int(len(prices)),
            "symbols": sorted(prices["symbol"].dropna().unique().tolist()),
            "date_start": prices["date"].min().isoformat() if not prices.empty else None,
            "date_end": prices["date"].max().isoformat() if not prices.empty else None,
            "bar_interval": "4h",
            "price_basis": basis,
        }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download 4h Binance perp research data set")
    parser.add_argument("--only", choices=["prices", "spot", "index", "funding", "oi", "caps", "tvl", "macro", "meta"], default=None)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    if args.only in (None, "prices"):
        prices = fetch_prices()
        prices.to_csv(OUT_DIR / "prices_4h_perp.csv", index=False)
        outputs["prices_4h_perp"] = str(OUT_DIR / "prices_4h_perp.csv")
    if args.only in (None, "spot"):
        spot = fetch_spot_prices()
        spot.to_csv(OUT_DIR / "spot_prices_4h.csv", index=False)
        outputs["spot_prices_4h"] = str(OUT_DIR / "spot_prices_4h.csv")
    if args.only in (None, "index"):
        index_prices = fetch_index_prices()
        index_prices.to_csv(OUT_DIR / "index_prices_4h.csv", index=False)
        outputs["index_prices_4h"] = str(OUT_DIR / "index_prices_4h.csv")
    if args.only in (None, "funding"):
        funding = fetch_funding_rates()
        funding.to_csv(OUT_DIR / "funding_rates_8h.csv", index=False)
        outputs["funding_rates_8h"] = str(OUT_DIR / "funding_rates_8h.csv")
    if args.only in (None, "oi"):
        oi = fetch_open_interest()
        oi.to_csv(OUT_DIR / "open_interest_8h.csv", index=False)
        outputs["open_interest_8h"] = str(OUT_DIR / "open_interest_8h.csv")
    if args.only in (None, "caps"):
        caps = fetch_market_caps()
        caps.to_csv(OUT_DIR / "market_caps.csv", index=False)
        outputs["market_caps"] = str(OUT_DIR / "market_caps.csv")
    if args.only in (None, "tvl"):
        tvl = fetch_tvl()
        tvl.to_csv(OUT_DIR / "tvl.csv", index=False)
        outputs["tvl"] = str(OUT_DIR / "tvl.csv")
    if args.only in (None, "macro"):
        macro = fetch_macro()
        macro.to_csv(OUT_DIR / "macro.csv", index=False)
        outputs["macro"] = str(OUT_DIR / "macro.csv")
    if args.only in (None, "meta"):
        meta = build_universe_meta()
        meta.to_csv(OUT_DIR / "universe_meta.csv", index=False)
        outputs["meta"] = str(OUT_DIR / "universe_meta.csv")

    manifest = build_data_manifest(outputs)
    (OUT_DIR / "data_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["data_manifest"] = str(OUT_DIR / "data_manifest.json")

    print(json.dumps({"state": "complete", "outputs": outputs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
