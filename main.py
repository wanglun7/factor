from __future__ import annotations

import argparse
import json
from pathlib import Path

from app_config import load_config
from data import build_provider, fetch, prepare
from research import (
    run_alpha_research_4h,
    run_ts_factor_research_4h,
    run_ts_walkforward_4h,
    validate_alpha_research_data_4h,
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


def validate_alpha_research_data_4h_command(config_path: str, line: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    report = validate_alpha_research_data_4h(panel, config.raw_generation, line=line)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run_alpha_research_4h_command(config_path: str, output_dir: str | None, line: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    base_output = output_dir or (
        Path(config.score_admission.output_dir).parent / f"alpha_research_{line}"
    )
    report = run_alpha_research_4h(
        panel=panel,
        raw_generation_config=config.raw_generation,
        score_admission_config=config.score_admission,
        composite_experiment_config=config.composite_experiment,
        scaled_alpha_config=config.scaled_alpha,
        output_dir=base_output,
        line=line,
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
    parser = argparse.ArgumentParser(description="4h alpha research stack")
    parser.add_argument("--config", default=str(Path("config/settings.yaml")))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-data-4h", help="Validate required 4h data inputs")
    validate_alpha = subparsers.add_parser("validate-alpha-research-data-4h", help="Validate generated alpha-research inputs")
    validate_alpha.add_argument("--line", choices=["descriptor", "rule", "both"], default="both")
    alpha_research = subparsers.add_parser("alpha-research-4h", help="Run generated alpha research on 4h data")
    alpha_research.add_argument("--line", choices=["descriptor", "rule", "both"], default="both")
    alpha_research.add_argument("--output-dir", default=None)
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
    if args.command == "validate-alpha-research-data-4h":
        validate_alpha_research_data_4h_command(args.config, args.line)
        return
    if args.command == "alpha-research-4h":
        run_alpha_research_4h_command(args.config, args.output_dir, args.line)
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
