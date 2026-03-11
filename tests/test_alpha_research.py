from __future__ import annotations

from pathlib import Path

import numpy as np
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
        scaled_alpha_config=config.scaled_alpha,
        position_mapping_config=config.position_mapping,
        execution_realism_config=config.execution_realism,
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
    assert (out_dir / "scaled_alpha_series.parquet").exists()
    assert (out_dir / "scaled_alpha_summary.csv").exists()
    assert (out_dir / "scaled_alpha_decision_log.md").exists()
    assert (out_dir / "scaled_alpha_evaluation.csv").exists()
    assert (out_dir / "scaled_alpha_bucket_diagnostics.csv").exists()
    assert (out_dir / "scaled_alpha_evaluation_log.md").exists()
    assert (out_dir / "position_mapping_series.parquet").exists()
    assert (out_dir / "position_mapping_variant_summary.csv").exists()
    assert (out_dir / "position_mapping_horse_race.csv").exists()
    assert (out_dir / "position_mapping_summary.csv").exists()
    assert (out_dir / "position_mapping_decision_log.md").exists()
    assert (out_dir / "execution_realism_series.parquet").exists()
    assert (out_dir / "execution_realism_path_summary.csv").exists()
    assert (out_dir / "execution_realism_variant_summary.csv").exists()
    assert (out_dir / "execution_realism_summary.csv").exists()
    assert (out_dir / "execution_realism_decision_log.md").exists()

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
    assert report["scaled_alpha_source_name"] == report["official_output_name"]
    assert report["scaled_alpha_verdict"] in {"strong_pass", "conditional_pass", "fail"}
    assert report["position_mapping_source_name"] == report["scaled_alpha_source_name"]
    assert report["position_mapping_variant"] in {"linear_target_only", "linear_band", "linear_band_vol_target"}
    assert report["position_mapping_winner_verdict"] in {"strong_win", "robust_win", "anchor_fallback"}
    assert report["execution_realism_source_name"] == report["position_mapping_source_name"]
    assert report["official_position_variant"] in {"linear_target_only", "linear_band", "linear_band_vol_target"}
    assert report["official_execution_variant"] == "lag_1_execution_with_state_cost"
    assert report["execution_realism_winner_verdict"] in {"strong_win", "robust_win", "anchor_fallback"}

    scaled_summary = pd.read_csv(out_dir / "scaled_alpha_summary.csv")
    assert {"source_name", "coverage_ratio", "scaled_alpha_clip_rate"}.issubset(scaled_summary.columns)
    assert scaled_summary.loc[0, "source_name"] == report["official_output_name"]

    scaled_eval = pd.read_csv(out_dir / "scaled_alpha_evaluation.csv")
    assert {
        "verdict",
        "scaled_alpha_rank_metric",
        "composite_to_scaled_rank_retention",
        "forecast_bucket_monotonicity",
        "bounded_output_ok",
        "min_live_coverage_ok",
    }.issubset(scaled_eval.columns)
    assert scaled_eval.loc[0, "verdict"] == report["scaled_alpha_verdict"]

    scaled_series = pd.read_parquet(out_dir / "scaled_alpha_series.parquet")
    assert {"composite_score", "forecast_return_30bar", "scaled_alpha"}.issubset(scaled_series.columns)
    valid_scaled = scaled_series["scaled_alpha"].dropna()
    assert valid_scaled.empty or ((valid_scaled >= -1.0) & (valid_scaled <= 1.0)).all()

    bucket_diag = pd.read_csv(out_dir / "scaled_alpha_bucket_diagnostics.csv")
    assert {"bucket", "sample_count", "mean_forward_return", "mean_value"}.issubset(bucket_diag.columns)

    position_variant_summary = pd.read_csv(out_dir / "position_mapping_variant_summary.csv")
    assert {"variant", "mean_turnover", "net_total_return", "sharpe"}.issubset(position_variant_summary.columns)
    assert set(position_variant_summary["variant"]) == {"linear_target_only", "linear_band", "linear_band_vol_target"}

    position_horse_race = pd.read_csv(out_dir / "position_mapping_horse_race.csv")
    assert {"variant", "anchor_variant", "verdict"}.issubset(position_horse_race.columns)
    assert set(position_horse_race["verdict"]).issubset({"anchor", "strong_win", "robust_win", "fail"})

    position_summary = pd.read_csv(out_dir / "position_mapping_summary.csv")
    assert {"source_name", "variant", "winner_verdict", "scaled_alpha_to_realized_corr"}.issubset(position_summary.columns)
    assert position_summary.loc[0, "source_name"] == report["scaled_alpha_source_name"]
    assert position_summary.loc[0, "variant"] == report["position_mapping_variant"]
    assert position_summary.loc[0, "winner_verdict"] == report["position_mapping_winner_verdict"]

    position_series = pd.read_parquet(out_dir / "position_mapping_series.parquet")
    assert {
        "variant",
        "scaled_alpha",
        "target_position",
        "realized_position",
        "turnover",
        "gross_return",
        "cost",
        "net_return",
    }.issubset(position_series.columns)
    valid_positions = position_series["realized_position"].dropna()
    assert valid_positions.empty or ((valid_positions >= -1.0) & (valid_positions <= 1.0)).all()

    execution_path_summary = pd.read_csv(out_dir / "execution_realism_path_summary.csv")
    assert {"mapping_variant", "path_name", "net_total_return", "sharpe"}.issubset(execution_path_summary.columns)
    assert set(execution_path_summary["mapping_variant"]) == {"linear_target_only", "linear_band", "linear_band_vol_target"}

    execution_variant_summary = pd.read_csv(out_dir / "execution_realism_variant_summary.csv")
    assert {
        "mapping_variant",
        "path_name",
        "net_total_return",
        "sharpe",
        "cost_drag",
        "verdict",
    }.issubset(execution_variant_summary.columns)
    assert set(execution_variant_summary["mapping_variant"]) == {"linear_target_only", "linear_band", "linear_band_vol_target"}
    assert set(execution_variant_summary["verdict"]).issubset({"anchor", "strong_win", "robust_win", "fail"})

    execution_summary = pd.read_csv(out_dir / "execution_realism_summary.csv")
    assert {
        "source_name",
        "official_position_variant",
        "official_execution_variant",
        "implementation_shortfall",
        "execution_lag_drag",
        "state_cost_drag",
        "delay_sensitivity_drag",
        "winner_verdict",
    }.issubset(execution_summary.columns)
    assert execution_summary.loc[0, "source_name"] == report["execution_realism_source_name"]
    assert execution_summary.loc[0, "official_position_variant"] == report["official_position_variant"]
    assert execution_summary.loc[0, "official_execution_variant"] == report["official_execution_variant"]
    assert execution_summary.loc[0, "winner_verdict"] == report["execution_realism_winner_verdict"]

    execution_series = pd.read_parquet(out_dir / "execution_realism_series.parquet")
    assert {
        "variant",
        "path_name",
        "paper_position",
        "executed_position",
        "effective_cost_bps",
        "gross_return",
        "net_return",
    }.issubset(execution_series.columns)
    variant_filter = "linear_target_only"
    lag1 = execution_series.loc[
        (execution_series["variant"] == variant_filter) & (execution_series["path_name"] == "lag_1_execution"),
        "executed_position",
    ].reset_index(drop=True)
    paper = execution_series.loc[
        (execution_series["variant"] == variant_filter) & (execution_series["path_name"] == "paper_position_path"),
        "paper_position",
    ].fillna(0.0).reset_index(drop=True)
    if len(lag1) > 1 and len(paper) > 1:
        assert np.allclose(lag1.iloc[1:].to_numpy(dtype=float), paper.iloc[:-1].to_numpy(dtype=float), equal_nan=True)
