from __future__ import annotations

import argparse
import json
from pathlib import Path

from app_config import load_config
from backtest import run_backtest, save_report_artifacts
from data import build_provider, fetch, prepare
from strategy import MomentumReversalSignal


def validate_data_command(config_path: str) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    fetch(config.data.start_date, config.data.end_date, provider)
    print(json.dumps({"status": "ok", "provider": config.data.provider, "csv_dir": config.data.csv_dir}, ensure_ascii=False))


def run_backtest_command(config_path: str, output_dir: str | None) -> None:
    config = load_config(config_path)
    provider = build_provider(config.data)
    bundle = fetch(config.data.start_date, config.data.end_date, provider)
    panel = prepare(bundle)
    signal = MomentumReversalSignal.from_config(config.strategy)
    result = run_backtest(
        panel=panel,
        signal=signal,
        universe_config=config.universe,
        portfolio_config=config.portfolio,
        backtest_config=config.backtest,
    )
    report = save_report_artifacts(result, output_dir or config.backtest.output_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Momentum/reversal research prototype")
    parser.add_argument("--config", default=str(Path("config/settings.yaml")))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-data", help="Validate that the minimal CSV inputs are present and readable")
    backtest_parser = subparsers.add_parser("backtest", help="Run the momentum/reversal backtest")
    backtest_parser.add_argument("--output-dir", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "validate-data":
        validate_data_command(args.config)
        return
    if args.command == "backtest":
        run_backtest_command(args.config, args.output_dir)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
