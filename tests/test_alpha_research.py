from __future__ import annotations

from pathlib import Path

import pandas as pd

from research import run_alpha_research_4h, validate_alpha_research_data_4h
from tests.utils import make_config, make_csv_dataset, make_panel


def test_validate_alpha_research_data_4h_reports_generated_lines(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    make_csv_dataset(root)
    panel = make_panel(root)
    config = make_config(root)

    report = validate_alpha_research_data_4h(panel, config.raw_generation, line="both")

    assert report["status"] == "ok"
    assert report["line"] == "both"
    assert report["generated_predictor_count"] > 100
    assert report["generator_lines"] == ["descriptor_based", "rule_grammar_based"]


def test_alpha_research_4h_writes_unified_artifacts_and_admission_fields(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    make_csv_dataset(root)
    panel = make_panel(root)
    config = make_config(root)

    report = run_alpha_research_4h(
        panel=panel,
        raw_generation_config=config.raw_generation,
        score_admission_config=config.score_admission,
        composite_experiment_config=config.composite_experiment,
        output_dir=tmp_path / "alpha_research_4h",
        line="both",
    )

    out_dir = tmp_path / "alpha_research_4h"
    assert report["state"] == "complete"
    assert (out_dir / "generated_raw_predictor_catalog.csv").exists()
    assert (out_dir / "generated_raw_predictor_summary.csv").exists()
    assert (out_dir / "standardized_score_summary.csv").exists()
    assert (out_dir / "composite_alpha_candidates.csv").exists()
    assert (out_dir / "composite_alpha_pruning.csv").exists()
    assert (out_dir / "composite_alpha_horse_race.csv").exists()
    assert (out_dir / "composite_alpha_panel.parquet").exists()
    assert (out_dir / "alpha_research_decision_log.md").exists()

    score_summary = pd.read_csv(out_dir / "standardized_score_summary.csv")
    assert {
        "integrity_tier",
        "admission_tier",
        "generator_line_rank_strength_ratio",
        "family_rank_strength_ratio",
        "delay_0_rank_metric",
        "retain_for_composite_v3",
    }.issubset(score_summary.columns)
    assert {"descriptor_based", "rule_grammar_based"} == set(score_summary["generator_line"].unique())
    assert "breakout_high_low_daily_200_score" in set(score_summary["score_name"])

    horse_race = pd.read_csv(out_dir / "composite_alpha_horse_race.csv")
    assert {"rank_metric", "rank_metric_ci_low", "rank_metric_ci_high"}.issubset(horse_race.columns)
    assert "anchor" in set(horse_race["object_type"])
    assert "diagnostic_full_composite" in set(horse_race["object_type"])
    assert report["official_output_name"]
