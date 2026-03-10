from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from app_config import DataConfig
from models import TSRawDataBundle


REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "price": ("date", "symbol", "open", "high", "low", "close", "volume", "vwap", "exchange"),
    "meta": ("symbol", "listing_date", "sector"),
}

OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "spot_price": ("date", "symbol", "open", "high", "low", "close", "volume", "vwap", "exchange"),
    "index_price": ("date", "symbol", "open", "high", "low", "close", "volume", "vwap", "exchange"),
    "funding": ("date", "symbol", "funding_rate"),
    "open_interest": ("date", "symbol", "open_interest"),
}


class MarketDataProvider(Protocol):
    def fetch_all(self, start: str, end: str) -> TSRawDataBundle: ...


def _read_csv(path: Path, required_columns: tuple[str, ...], *, allow_missing: bool = False) -> pd.DataFrame:
    if not path.exists():
        if allow_missing:
            return pd.DataFrame(columns=list(required_columns))
        raise FileNotFoundError(f"Missing required data file: {path}")
    frame = pd.read_csv(path)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {missing}")
    return frame


def _parse_timestamp_column(frame: pd.DataFrame) -> pd.DataFrame:
    parsed = frame.copy()
    if "date" in parsed.columns:
        date_series = pd.to_datetime(parsed["date"], utc=True, errors="coerce")
        parsed["date"] = date_series.dt.tz_convert(None)
    return parsed


@dataclass(slots=True)
class LocalCsvProvider:
    root: Path
    config: DataConfig

    def fetch_all(self, start: str, end: str) -> TSRawDataBundle:
        required_price = _read_csv(self.root / self.config.price_file, REQUIRED_COLUMNS["price"])
        required_meta = _read_csv(self.root / "universe_meta.csv", REQUIRED_COLUMNS["meta"])
        optional_spot = _read_csv(self.root / self.config.spot_price_file, OPTIONAL_COLUMNS["spot_price"], allow_missing=True)
        optional_index = _read_csv(self.root / self.config.index_price_file, OPTIONAL_COLUMNS["index_price"], allow_missing=True)
        optional_funding = _read_csv(self.root / self.config.funding_file, OPTIONAL_COLUMNS["funding"], allow_missing=True)
        optional_oi = _read_csv(self.root / self.config.open_interest_file, OPTIONAL_COLUMNS["open_interest"], allow_missing=True)

        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)

        def _filter(frame: pd.DataFrame) -> pd.DataFrame:
            if "date" not in frame.columns:
                return frame.copy()
            filtered = _parse_timestamp_column(frame)
            filtered = filtered.loc[filtered["date"].between(start_ts, end_ts)].copy()
            return filtered

        return TSRawDataBundle(
            prices=_filter(required_price),
            spot_prices=_filter(optional_spot),
            index_prices=_filter(optional_index),
            universe_meta=required_meta.copy(),
            funding_rates=_filter(optional_funding),
            open_interest=_filter(optional_oi),
        )


def build_provider(config: DataConfig) -> MarketDataProvider:
    if config.provider != "local_csv":
        raise ValueError("The research prototype only supports local CSV data.")
    return LocalCsvProvider(root=Path(config.csv_dir), config=config)


def fetch(start: str, end: str, provider: MarketDataProvider) -> TSRawDataBundle:
    return provider.fetch_all(start=start, end=end)
