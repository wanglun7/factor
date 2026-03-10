from __future__ import annotations

from pathlib import Path

from data import prepare
from data.fetcher import LocalCsvProvider, fetch
from tests.utils import make_config, make_csv_dataset


def test_prepare_adds_4h_features_and_optional_sources(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    config = make_config(tmp_path)
    provider = LocalCsvProvider(root=tmp_path, config=config.data)
    bundle = fetch(start=config.data.start_date, end=config.data.end_date, provider=provider)

    panel = prepare(bundle)
    assert "ema_120" in panel.frame.columns
    assert "spot_close" in panel.frame.columns
    assert "index_close" in panel.frame.columns
    assert "avg_funding_21period" in panel.frame.columns
    assert "funding_rate_lag1" in panel.frame.columns
    assert panel.frame["ret_120bar"].notna().sum() > 0
    assert panel.frame["breakout_360bar"].notna().sum() > 0


def test_prepare_handles_missing_optional_files(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    (tmp_path / "funding_rates_8h.csv").unlink()
    (tmp_path / "spot_prices_4h.csv").unlink()
    (tmp_path / "index_prices_4h.csv").unlink()
    config = make_config(tmp_path)
    provider = LocalCsvProvider(root=tmp_path, config=config.data)
    bundle = fetch(start=config.data.start_date, end=config.data.end_date, provider=provider)

    panel = prepare(bundle)
    assert panel.frame["spot_close"].notna().sum() == 0
    assert panel.frame["index_close"].notna().sum() == 0
    assert panel.frame["avg_funding_21period"].notna().sum() == 0
    assert panel.frame["oi_change_21period"].notna().sum() == 0
