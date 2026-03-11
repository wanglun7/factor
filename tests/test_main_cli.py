from __future__ import annotations

from main import build_parser


def test_parser_accepts_4h_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["validate-data-4h"]).command == "validate-data-4h"
    assert parser.parse_args(["validate-alpha-research-data-4h"]).command == "validate-alpha-research-data-4h"
    assert parser.parse_args(["alpha-research-4h"]).command == "alpha-research-4h"
    assert parser.parse_args(["ts-factor-research-4h"]).command == "ts-factor-research-4h"
    assert parser.parse_args(["ts-walkforward-4h"]).command == "ts-walkforward-4h"
