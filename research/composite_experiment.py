from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app_config import CompositeExperimentConfig
from research.signal_metrics import (
    forward_return,
    monotonicity_for_values,
    rank_metric_with_block_bootstrap,
    spread_for_predictor,
    stability_score,
)


def _evaluate_series(
    name: str,
    series: pd.Series,
    forward_0: pd.Series,
    forward_1: pd.Series,
    forward_2: pd.Series,
    config: CompositeExperimentConfig,
    families: list[str],
    members: list[str],
    score_weights: dict[str, float],
) -> dict[str, object]:
    delay_0_spread = spread_for_predictor(series, forward_0, "continuous")
    delay_1_spread = spread_for_predictor(series, forward_1, "continuous")
    delay_2_spread = spread_for_predictor(series, forward_2, "continuous")
    delay_0_rank_metric, rank_metric_ci_low, rank_metric_ci_high = rank_metric_with_block_bootstrap(
        series,
        forward_0,
        block_size=config.bootstrap_block_size,
        n_boot=config.bootstrap_samples,
        seed=config.bootstrap_seed,
    )
    delay_1_rank_metric = rank_metric_with_block_bootstrap(
        series,
        forward_1,
        block_size=config.bootstrap_block_size,
        n_boot=max(2, config.bootstrap_samples // 4),
        seed=config.bootstrap_seed + 1,
    )[0]
    delay_2_rank_metric = rank_metric_with_block_bootstrap(
        series,
        forward_2,
        block_size=config.bootstrap_block_size,
        n_boot=max(2, config.bootstrap_samples // 4),
        seed=config.bootstrap_seed + 2,
    )[0]
    weights = np.array(list(score_weights.values()), dtype=float)
    return {
        "name": name,
        "delay_0_spread": delay_0_spread,
        "delay_1_spread": delay_1_spread,
        "delay_2_spread": delay_2_spread,
        "rank_metric": delay_0_rank_metric,
        "delay_1_rank_metric": delay_1_rank_metric,
        "delay_2_rank_metric": delay_2_rank_metric,
        "rank_metric_ci_low": rank_metric_ci_low,
        "rank_metric_ci_high": rank_metric_ci_high,
        "monotonicity_ratio": monotonicity_for_values(series, forward_0, "continuous"),
        "coverage_ratio": float(series.notna().mean()),
        "family_count": len(set(families)),
        "effective_score_count": len(members),
        "member_scores": "|".join(members),
        "families": "|".join(sorted(set(families))),
        "score_contribution_concentration": float(np.square(np.abs(weights)).sum()) if len(weights) else 0.0,
        "max_single_score_weight": float(np.max(np.abs(weights))) if len(weights) else 0.0,
        "stability_score": stability_score(delay_0_rank_metric, delay_1_rank_metric, delay_2_rank_metric),
    }


def _prune_family(
    family_frame: pd.DataFrame,
    score_frame: pd.DataFrame,
    threshold: float,
    max_scores_per_family: int,
) -> tuple[list[str], list[dict[str, object]]]:
    ranked = family_frame.sort_values(["delay_0_rank_metric", "generator_line_rank_strength_ratio"], ascending=[False, False]).reset_index(drop=True)
    columns = ranked["score_name"].tolist()
    corr = score_frame[columns].corr() if len(columns) > 1 else pd.DataFrame(index=columns, columns=columns, data=1.0)
    kept: list[str] = []
    rows: list[dict[str, object]] = []
    for row in ranked.itertuples(index=False):
        remove_reason = ""
        redundant_with = ""
        for kept_name in kept:
            corr_value = float(corr.loc[row.score_name, kept_name])
            if pd.notna(corr_value) and abs(corr_value) >= threshold:
                remove_reason = "redundant_corr"
                redundant_with = kept_name
                break
        if not remove_reason and len(kept) >= max_scores_per_family:
            remove_reason = "family_cap"
        if not remove_reason:
            kept.append(row.score_name)
        rows.append(
            {
                "generator_line": row.generator_line,
                "family": row.family,
                "score_name": row.score_name,
                "rank_within_family": len(rows) + 1,
                "delay_0_rank_metric": row.delay_0_rank_metric,
                "generator_line_rank_strength_ratio": row.generator_line_rank_strength_ratio,
                "family_rank_strength_ratio": row.family_rank_strength_ratio,
                "kept": remove_reason == "",
                "remove_reason": remove_reason or "kept",
                "redundant_with": redundant_with,
            }
        )
    return kept, rows


def _decision_log(score_summary: pd.DataFrame, pruning: pd.DataFrame, horse_race: pd.DataFrame, official_name: str) -> str:
    lines = ["# Alpha Research Decision Log", ""]
    lines.append("## Admitted Scores")
    admitted = score_summary.loc[score_summary["retain_for_composite_v3"] == True].sort_values(
        ["generator_line", "family", "delay_0_rank_metric"], ascending=[True, True, False]
    )
    if admitted.empty:
        lines.append("- none")
    else:
        for row in admitted.itertuples(index=False):
            lines.append(
                f"- `{row.score_name}` ({row.generator_line}, {row.family}, {row.admission_tier}, rank={row.delay_0_rank_metric:.4f})"
            )
    lines.append("")
    lines.append("## Family Retention")
    if pruning.empty:
        lines.append("- none")
    else:
        for family, subset in pruning.groupby("family", sort=True):
            kept = subset.loc[subset["kept"] == True, "score_name"].tolist()
            lines.append(f"- `{family}`: {', '.join(kept) if kept else 'none'}")
    lines.append("")
    lines.append("## Horse Race")
    for row in horse_race.sort_values(["object_type", "rank_metric"], ascending=[True, False]).itertuples(index=False):
        lines.append(
            f"- `{row.name}`: {row.verdict}, rank={row.rank_metric:.4f}, "
            f"ci=[{row.rank_metric_ci_low:.4f}, {row.rank_metric_ci_high:.4f}], stability={row.stability_score:.3f}"
        )
    lines.append("")
    lines.append(f"## Official Output\n- `{official_name}`")
    return "\n".join(lines).rstrip() + "\n"


def run_composite_experiment(
    score_summary: pd.DataFrame,
    score_frame: pd.DataFrame,
    base_price_frame: pd.DataFrame,
    config: CompositeExperimentConfig,
    output_dir: str | Path,
) -> dict[str, object]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    candidates = score_summary.loc[score_summary["retain_for_composite_v3"] == True].copy()
    if candidates.empty:
        raise ValueError("No admitted scores available for composite experiment.")

    forward_0 = forward_return(base_price_frame, config.primary_horizon, 0)
    forward_1 = forward_return(base_price_frame, config.primary_horizon, 1)
    forward_2 = forward_return(base_price_frame, config.primary_horizon, 2)

    pruning_rows: list[dict[str, object]] = []
    family_kept: dict[str, list[str]] = {}
    for _, family_frame in candidates.groupby(["generator_line", "family"], sort=True):
        kept, rows = _prune_family(family_frame, score_frame, config.redundancy_corr_threshold, config.max_scores_per_family)
        family_name = str(family_frame["family"].iloc[0])
        family_kept[family_name] = kept
        pruning_rows.extend(rows)
    pruning = pd.DataFrame(pruning_rows).sort_values(["generator_line", "family", "rank_within_family"]).reset_index(drop=True)

    surviving = [score for scores in family_kept.values() for score in scores]
    if not surviving:
        raise ValueError("No scores survive family pruning.")

    anchor_row = candidates.sort_values(["delay_0_rank_metric", "generator_line_rank_strength_ratio"], ascending=[False, False]).iloc[0]
    anchor_name = str(anchor_row["score_name"])
    anchor_family = str(anchor_row["family"])
    horse_rows: list[dict[str, object]] = []
    panel_out = score_frame.reset_index()[["date", "symbol", *surviving]].copy()

    anchor_metrics = _evaluate_series(
        anchor_name,
        score_frame[anchor_name],
        forward_0,
        forward_1,
        forward_2,
        config,
        [anchor_family],
        [anchor_name],
        {anchor_name: 1.0},
    )
    anchor_metrics["object_type"] = "anchor"
    anchor_metrics["verdict"] = "baseline"
    horse_rows.append(anchor_metrics)

    family_subcomposites: dict[str, pd.Series] = {}
    family_member_weights: dict[str, dict[str, float]] = {}
    for family, kept in family_kept.items():
        if not kept:
            continue
        family_name = f"{family}_subcomposite"
        if config.ic_weighted_subcomposite and len(kept) > 1:
            ic_vals = candidates.set_index("score_name").loc[kept, "delay_0_rank_metric"].clip(lower=0.0)
            ic_total = float(ic_vals.sum())
            if ic_total > 0.0:
                ic_w = (ic_vals / ic_total).to_dict()
                family_series = sum(score_frame[s] * w for s, w in ic_w.items())  # type: ignore[assignment]
                member_w = ic_w
            else:
                family_series = score_frame[kept].mean(axis=1, skipna=True)
                member_w = {s: 1.0 / len(kept) for s in kept}
        else:
            family_series = score_frame[kept].mean(axis=1, skipna=True)
            member_w = {s: 1.0 / len(kept) for s in kept}
        family_subcomposites[family] = family_series
        family_member_weights[family] = member_w
        panel_out[family_name] = family_series.to_numpy()
        metrics = _evaluate_series(
            family_name,
            family_series,
            forward_0,
            forward_1,
            forward_2,
            config,
            [family],
            kept,
            member_w,
        )
        metrics["object_type"] = "family_subcomposite"
        horse_rows.append(metrics)

    for family, family_series in family_subcomposites.items():
        if family == anchor_family:
            continue
        member_scores = family_kept[family]
        sat_member_w = family_member_weights[family]
        for weight in config.anchor_satellite_weights:
            name = f"anchor_plus_{family}_w{int(round(weight * 100)):02d}"
            composite = (1.0 - weight) * score_frame[anchor_name] + weight * family_series
            panel_out[name] = composite.to_numpy()
            member_weights = {anchor_name: 1.0 - weight}
            for score_name, sat_w in sat_member_w.items():
                member_weights[score_name] = weight * sat_w
            metrics = _evaluate_series(
                name,
                composite,
                forward_0,
                forward_1,
                forward_2,
                config,
                [anchor_family, family],
                [anchor_name, *member_scores],
                member_weights,
            )
            metrics["object_type"] = "anchor_plus_family"
            horse_rows.append(metrics)

    # top-2 non-anchor families combined as a single satellite
    non_anchor_with_metric = [
        (family, series, float(next((r["rank_metric"] for r in horse_rows if r.get("name") == f"{family}_subcomposite"), 0.0)))
        for family, series in family_subcomposites.items()
        if family != anchor_family
    ]
    non_anchor_with_metric.sort(key=lambda x: x[2], reverse=True)
    if len(non_anchor_with_metric) >= 2:
        fam1, series1, _ = non_anchor_with_metric[0]
        fam2, series2, _ = non_anchor_with_metric[1]
        both_scores = family_kept[fam1] + family_kept[fam2]
        for weight in config.anchor_satellite_weights:
            name = f"anchor_plus_{fam1}_and_{fam2}_w{int(round(weight * 100)):02d}"
            satellite = 0.5 * series1 + 0.5 * series2
            composite = (1.0 - weight) * score_frame[anchor_name] + weight * satellite
            panel_out[name] = composite.to_numpy()
            mw: dict[str, float] = {anchor_name: 1.0 - weight}
            for s, w2 in family_member_weights[fam1].items():
                mw[s] = weight * 0.5 * w2
            for s, w2 in family_member_weights[fam2].items():
                mw[s] = weight * 0.5 * w2
            metrics = _evaluate_series(
                name,
                composite,
                forward_0,
                forward_1,
                forward_2,
                config,
                [anchor_family, fam1, fam2],
                [anchor_name, *both_scores],
                mw,
            )
            metrics["object_type"] = "anchor_plus_two_families"
            horse_rows.append(metrics)

    if family_subcomposites:
        full_series = pd.concat(list(family_subcomposites.values()), axis=1).mean(axis=1, skipna=True)
        panel_out["full_family_neutral_composite"] = full_series.to_numpy()
        full_weights: dict[str, float] = {}
        family_weight = 1.0 / len(family_subcomposites)
        for family, scores in family_kept.items():
            if not scores:
                continue
            per_score = family_weight / len(scores)
            for score_name in scores:
                full_weights[score_name] = per_score
        metrics = _evaluate_series(
            "full_family_neutral_composite",
            full_series,
            forward_0,
            forward_1,
            forward_2,
            config,
            [family for family, scores in family_kept.items() if scores],
            surviving,
            full_weights,
        )
        metrics["object_type"] = "diagnostic_full_composite"
        horse_rows.append(metrics)

    horse_race = pd.DataFrame(horse_rows)
    verdicts: list[str] = []
    anchor_rank = float(anchor_metrics["rank_metric"])
    anchor_stability = float(anchor_metrics["stability_score"])
    for row in horse_race.itertuples(index=False):
        if row.object_type == "anchor":
            verdicts.append("baseline")
            continue
        strong = row.rank_metric > anchor_rank and row.rank_metric_ci_low > 0.0 and row.stability_score >= anchor_stability
        robust = (
            row.rank_metric >= config.robust_relative_strength_floor * anchor_rank
            and row.rank_metric_ci_low > 0.0
            and row.stability_score >= (1.0 + config.robust_stability_improvement_min) * anchor_stability
            and row.family_count >= 2
            and row.max_single_score_weight <= 0.9
        )
        verdicts.append("strong_win" if strong else "robust_win" if robust else "fail")
    horse_race["verdict"] = verdicts

    contenders = horse_race.loc[horse_race["verdict"].isin(["strong_win", "robust_win"])].copy()
    if contenders.empty:
        official_name = anchor_name
        official_verdict = "anchor_fallback"
    else:
        contenders["priority"] = contenders["verdict"].map({"strong_win": 2, "robust_win": 1})
        best = contenders.sort_values(["priority", "rank_metric", "stability_score"], ascending=[False, False, False]).iloc[0]
        official_name = str(best["name"])
        official_verdict = str(best["verdict"])

    candidates.to_csv(target / "composite_alpha_candidates.csv", index=False)
    pruning.to_csv(target / "composite_alpha_pruning.csv", index=False)
    horse_race.to_csv(target / "composite_alpha_horse_race.csv", index=False)
    panel_out.to_parquet(target / "composite_alpha_panel.parquet", index=False)
    (target / "alpha_research_decision_log.md").write_text(_decision_log(score_summary, pruning, horse_race, official_name), encoding="utf-8")

    return {
        "horse_race": horse_race,
        "pruning": pruning,
        "anchor_name": anchor_name,
        "official_output_name": official_name,
        "official_output_verdict": official_verdict,
    }
