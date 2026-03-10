from __future__ import annotations

import argparse
import json
from pathlib import Path

from app_config import load_config
from data import build_provider, fetch, prepare
from research import (
    run_continuous_score_experiment_4h,
    run_raw_predictor_research_4h,
    run_standardized_score_research_4h,
    run_ts_factor_research_4h,
    run_ts_walkforward_4h,
    validate_continuous_score_experiment_data_4h,
    validate_raw_predictor_data_4h,
    validate_standardized_score_data_4h,
)


def validate_data_4h_command(config_path: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    optional_sources = []
    if not bundle.funding_rates.empty:
        optional_sources.append("funding_rates_8h")
    if not bundle.open_interest.empty:
        optional_sources.append("open_interest_8h")
    print(
        json.dumps(
            {
                "status": "ok",
                "provider": config.data.provider,
                "csv_dir": config.data.csv_dir,
                "bar_interval": config.data.bar_interval,
                "price_basis": config.data.price_basis,
                "price_file": config.data.price_file,
                "optional_sources": optional_sources,
            },
            ensure_ascii=False,
        )
    )


def validate_raw_predictor_data_4h_command(config_path: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = validate_raw_predictor_data_4h(panel, config.ts_universe)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_raw_predictor_research_4h_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = run_raw_predictor_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.raw_predictors,
        output_dir=output_dir or config.raw_predictors.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def validate_standardized_score_data_4h_command(config_path: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = validate_standardized_score_data_4h(panel, config.ts_universe, config.standardized_scores)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_standardized_score_research_4h_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = run_standardized_score_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.standardized_scores,
        output_dir=output_dir or config.standardized_scores.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def validate_continuous_score_experiment_data_4h_command(config_path: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = validate_continuous_score_experiment_data_4h(panel, config.ts_universe, config.continuous_score_experiment)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_continuous_score_experiment_4h_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = run_continuous_score_experiment_4h(
        panel=panel,
        universe_config=config.ts_universe,
        config=config.continuous_score_experiment,
        output_dir=output_dir or config.continuous_score_experiment.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_ts_factor_research_4h_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = run_ts_factor_research_4h(
        panel=panel,
        universe_config=config.ts_universe,
        research_config=config.ts_research,
        backtest_config=config.ts_backtest,
        output_dir=output_dir or config.ts_research.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_ts_walkforward_4h_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = run_ts_walkforward_4h(
        panel=panel,
        universe_config=config.ts_universe,
        research_config=config.ts_research,
        backtest_config=config.ts_backtest,
        output_dir=output_dir or config.ts_backtest.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4h time-series alpha research prototype")
    parser.add_argument("--config", default=str(Path("config/settings.yaml")))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-data-4h", help="Validate required 4h data inputs")
    subparsers.add_parser("validate-raw-predictor-data-4h", help="Validate raw predictor data inputs")
    subparsers.add_parser("validate-standardized-score-data-4h", help="Validate standardized score data inputs")
    subparsers.add_parser("validate-continuous-score-experiment-data-4h", help="Validate continuous score experiment inputs")
    raw_predictor_parser = subparsers.add_parser("raw-predictor-research-4h", help="Run raw predictor catalog and research on 4h data")
    raw_predictor_parser.add_argument("--output-dir", default=None)
    standardized_score_parser = subparsers.add_parser("standardized-score-research-4h", help="Run standardized score research on 4h data")
    standardized_score_parser.add_argument("--output-dir", default=None)
    continuous_score_parser = subparsers.add_parser("continuous-score-experiment-4h", help="Run continuous score method comparison on 4h data")
    continuous_score_parser.add_argument("--output-dir", default=None)
    ts_research_parser = subparsers.add_parser("ts-factor-research-4h", help="Run 4h time-series factor discovery research")
    ts_research_parser.add_argument("--output-dir", default=None)
    ts_walkforward_parser = subparsers.add_parser("ts-walkforward-4h", help="Run 4h expanding-window walkforward evaluation")
    ts_walkforward_parser.add_argument("--output-dir", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "validate-data-4h":
        validate_data_4h_command(args.config)
        return
    if args.command == "validate-raw-predictor-data-4h":
        validate_raw_predictor_data_4h_command(args.config)
        return
    if args.command == "validate-standardized-score-data-4h":
        validate_standardized_score_data_4h_command(args.config)
        return
    if args.command == "validate-continuous-score-experiment-data-4h":
        validate_continuous_score_experiment_data_4h_command(args.config)
        return
    if args.command == "raw-predictor-research-4h":
        run_raw_predictor_research_4h_command(args.config, args.output_dir)
        return
    if args.command == "standardized-score-research-4h":
        run_standardized_score_research_4h_command(args.config, args.output_dir)
        return
    if args.command == "continuous-score-experiment-4h":
        run_continuous_score_experiment_4h_command(args.config, args.output_dir)
        return
    if args.command == "ts-factor-research-4h":
        run_ts_factor_research_4h_command(args.config, args.output_dir)
        return
    if args.command == "ts-walkforward-4h":
        run_ts_walkforward_4h_command(args.config, args.output_dir)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
