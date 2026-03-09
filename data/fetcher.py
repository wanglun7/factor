from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from app_config import DataConfig
from models import RawDataBundle


REQUIRED_FILES: dict[str, tuple[str, ...]] = {
    "prices.csv": ("date", "symbol", "open", "high", "low", "close", "volume", "vwap", "exchange"),
    "universe_meta.csv": ("symbol", "listing_date", "sector"),
}


class MarketDataProvider(Protocol):
    def fetch_all(self, start: str, end: str) -> RawDataBundle: ...


def _read_csv(path: Path, required_columns: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required data file: {path}")
    frame = pd.read_csv(path)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {missing}")
    return frame


@dataclass(slots=True)
class LocalCsvProvider:
    root: Path

    def fetch_all(self, start: str, end: str) -> RawDataBundle:
        files = {name: _read_csv(self.root / name, columns) for name, columns in REQUIRED_FILES.items()}
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        prices = files["prices.csv"].copy()
        prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
        prices = prices.loc[prices["date"].between(start_ts, end_ts)].copy()
        return RawDataBundle(
            prices=prices,
            universe_meta=files["universe_meta.csv"].copy(),
        )


def build_provider(config: DataConfig) -> MarketDataProvider:
    if config.provider != "local_csv":
        raise ValueError("The research prototype only supports local CSV data.")
    return LocalCsvProvider(root=Path(config.csv_dir))


def fetch(start: str, end: str, provider: MarketDataProvider) -> RawDataBundle:
    return provider.fetch_all(start=start, end=end)
