from __future__ import annotations

from pathlib import Path

import pytest

from data.fetcher import LocalCsvProvider, fetch
from tests.utils import make_csv_dataset, make_panel


def test_local_csv_provider_requires_real_files(tmp_path: Path) -> None:
    provider = LocalCsvProvider(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        fetch(start="2021-01-01", end="2021-06-01", provider=provider)


def test_prepare_builds_phase1_features(tmp_path: Path) -> None:
    make_csv_dataset(tmp_path)
    panel = make_panel(tmp_path)
    final_slice = panel.cross_section(panel.dates[-1])

    expected_columns = {
        "return_1d",
        "ret_3d",
        "ret_20d",
        "avg_dollar_volume_30d",
        "days_listed",
    }
    assert expected_columns.issubset(set(panel.frame.columns))
    assert final_slice["ret_20d"].notna().all()
    assert final_slice["days_listed"].min() >= 90
