from __future__ import annotations

import pandas as pd

from app_config import UniverseConfig
from models import AlignedPanel


def build_universe(panel: AlignedPanel, asof_date: pd.Timestamp, config: UniverseConfig) -> list[str]:
    cross_section = panel.cross_section(asof_date)
    eligible = cross_section.loc[cross_section["days_listed"] >= config.min_listing_days].copy()
    eligible = eligible.loc[eligible["avg_dollar_volume_30d"].fillna(0.0) >= config.min_avg_dollar_volume]
    ranked = eligible.sort_values("avg_dollar_volume_30d", ascending=False)
    return ranked.head(config.selection_size).index.tolist()
