from __future__ import annotations

import pytest

from main import build_parser


def test_parser_only_exposes_validate_data_and_backtest() -> None:
    parser = build_parser()
    backtest_args = parser.parse_args(["backtest"])
    validate_args = parser.parse_args(["validate-data"])

    assert backtest_args.command == "backtest"
    assert validate_args.command == "validate-data"

    with pytest.raises(SystemExit):
        parser.parse_args(["analyze"])
    with pytest.raises(SystemExit):
        parser.parse_args(["experiments"])
