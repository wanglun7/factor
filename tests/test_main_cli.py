from __future__ import annotations

from main import build_parser


def test_parser_accepts_4h_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["validate-data-4h"]).command == "validate-data-4h"
    assert parser.parse_args(["validate-raw-predictor-data-4h"]).command == "validate-raw-predictor-data-4h"
    assert parser.parse_args(["validate-standardized-score-data-4h"]).command == "validate-standardized-score-data-4h"
    assert parser.parse_args(["validate-continuous-score-experiment-data-4h"]).command == "validate-continuous-score-experiment-data-4h"
    assert parser.parse_args(["raw-predictor-research-4h"]).command == "raw-predictor-research-4h"
    assert parser.parse_args(["standardized-score-research-4h"]).command == "standardized-score-research-4h"
    assert parser.parse_args(["continuous-score-experiment-4h"]).command == "continuous-score-experiment-4h"
    assert parser.parse_args(["ts-factor-research-4h"]).command == "ts-factor-research-4h"
    assert parser.parse_args(["ts-walkforward-4h"]).command == "ts-walkforward-4h"
