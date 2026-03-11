from __future__ import annotations

from pathlib import Path

import pandas as pd

from app_config import CompositeExperimentConfig, RawGenerationConfig, ScaledAlphaConfig, ScoreAdmissionConfig
from models import AlignedPanel
from research.composite_experiment import run_composite_experiment
from research.generated_raw import build_generated_raw, write_raw_artifacts
from research.scaled_alpha import run_scaled_alpha
from research.score_admission import run_score_admission


def validate_alpha_research_data_4h(panel: AlignedPanel, config: RawGenerationConfig, line: str = "both") -> dict[str, object]:
    generated = build_generated_raw(panel, config, line=line)
    catalog = generated["catalog"]
    raw_frame = generated["raw_frame"]
    assert isinstance(catalog, pd.DataFrame)
    assert isinstance(raw_frame, pd.DataFrame)
    return {
        "status": "ok",
        "line": line,
        "symbols": generated["symbols"],
        "generated_predictor_count": len(catalog),
        "generator_lines": sorted(catalog["generator_line"].dropna().unique().tolist()),
        "family_count": int(catalog["family"].nunique()),
    }


def run_alpha_research_4h(
    panel: AlignedPanel,
    raw_generation_config: RawGenerationConfig,
    score_admission_config: ScoreAdmissionConfig,
    composite_experiment_config: CompositeExperimentConfig,
    scaled_alpha_config: ScaledAlphaConfig,
    output_dir: str | Path,
    line: str = "both",
) -> dict[str, object]:
    generated = build_generated_raw(panel, raw_generation_config, line=line)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_raw_artifacts(generated, target)

    catalog = generated["catalog"]
    raw_frame = generated["raw_frame"]
    raw_summary = generated["raw_summary"]
    assert isinstance(catalog, pd.DataFrame)
    assert isinstance(raw_frame, pd.DataFrame)
    assert isinstance(raw_summary, pd.DataFrame)

    score_result = run_score_admission(
        raw_catalog=catalog,
        raw_frame=raw_frame,
        config=score_admission_config,
        output_dir=target,
    )
    score_frame = score_result["score_frame"]
    score_summary = score_result["score_summary"]
    assert isinstance(score_frame, pd.DataFrame)
    assert isinstance(score_summary, pd.DataFrame)

    base_price_frame = raw_frame.reset_index()[["date", "symbol", "close"]]
    composite_result = run_composite_experiment(
        score_summary=score_summary,
        score_frame=score_frame,
        base_price_frame=base_price_frame,
        config=composite_experiment_config,
        output_dir=target,
    )
    horse_race = composite_result["horse_race"]
    composite_panel = composite_result["panel"]
    assert isinstance(horse_race, pd.DataFrame)
    assert isinstance(composite_panel, pd.DataFrame)

    scaled_alpha_result = run_scaled_alpha(
        composite_panel=composite_panel,
        official_output_name=str(composite_result["official_output_name"]),
        base_price_frame=base_price_frame,
        config=scaled_alpha_config,
        output_dir=target,
    )
    scaled_alpha_summary = scaled_alpha_result["summary"]
    assert isinstance(scaled_alpha_summary, pd.DataFrame)

    return {
        "state": "complete",
        "line": line,
        "generated_predictor_count": len(catalog),
        "admitted_score_count": int(score_summary["retain_for_composite_v3"].sum()),
        "anchor_name": composite_result["anchor_name"],
        "official_output_name": composite_result["official_output_name"],
        "official_output_verdict": composite_result["official_output_verdict"],
        "scaled_alpha_source_name": scaled_alpha_result["source_name"],
        "scaled_alpha_verdict": scaled_alpha_result["verdict"],
        "artifacts": {
            "raw_catalog": "generated_raw_predictor_catalog.csv",
            "raw_summary": "generated_raw_predictor_summary.csv",
            "score_summary": "standardized_score_summary.csv",
            "score_panel": "standardized_score_panel.parquet",
            "composite_candidates": "composite_alpha_candidates.csv",
            "composite_pruning": "composite_alpha_pruning.csv",
            "composite_horse_race": "composite_alpha_horse_race.csv",
            "composite_panel": "composite_alpha_panel.parquet",
            "decision_log": "alpha_research_decision_log.md",
            "scaled_alpha_series": "scaled_alpha_series.parquet",
            "scaled_alpha_summary": "scaled_alpha_summary.csv",
            "scaled_alpha_decision_log": "scaled_alpha_decision_log.md",
            "scaled_alpha_evaluation": "scaled_alpha_evaluation.csv",
            "scaled_alpha_bucket_diagnostics": "scaled_alpha_bucket_diagnostics.csv",
            "scaled_alpha_evaluation_log": "scaled_alpha_evaluation_log.md",
        },
    }
