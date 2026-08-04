"""Command-line adapter for strict TREC retrieval-system comparison."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rankweave.comparison import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_RANDOMIZATION_COUNT,
    NDCG_AT_K_METRIC,
    SUPPORTED_COMPARISON_ALTERNATIVES,
    SUPPORTED_COMPARISON_METRICS,
    TWO_SIDED_ALTERNATIVE,
)
from rankweave.trec_comparison import (
    TrecRunComparisonReport,
    compare_trec_runs,
)

OUTPUT_SCHEMA_VERSION = "rankweave.trec-comparison.v1"
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
_SIGNED_DECIMAL_PATTERN = re.compile(r"[+-]?[0-9]+")


class _UsageError(ValueError):
    """Internal exception used to convert argparse failures into exit code 2."""


class _ArgumentParser(argparse.ArgumentParser):
    """Argument parser that reports usage failures through ``main``."""

    def error(self, message: str) -> None:
        """Raise a testable usage exception instead of terminating directly."""
        raise _UsageError(message)


def _positive_integer_parser(label: str):
    """Return an argparse converter for a labelled positive decimal integer."""

    def parse_positive_integer(raw_value: str) -> int:
        """Parse one positive ASCII decimal integer for the enclosing label."""
        if not raw_value.isascii() or not raw_value.isdecimal():
            raise argparse.ArgumentTypeError(
                f"{label} must be a positive integer"
            )
        parsed_value = int(raw_value)
        if parsed_value < 1:
            raise argparse.ArgumentTypeError(
                f"{label} must be a positive integer"
            )
        return parsed_value

    return parse_positive_integer


def _integer_seed(raw_value: str) -> int:
    """Parse a signed ASCII decimal random seed."""
    if _SIGNED_DECIMAL_PATTERN.fullmatch(raw_value) is None:
        raise argparse.ArgumentTypeError("seed must be an integer")
    return int(raw_value)


def build_parser() -> argparse.ArgumentParser:
    """Build the stable RankWeave command-line parser."""
    parser = _ArgumentParser(
        prog="rankweave",
        description=(
            "Strict, dependency-free retrieval fusion and evaluation tools."
        ),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    compare_parser = subcommands.add_parser(
        "compare",
        help="compare a baseline and candidate TREC run against shared qrels",
    )
    compare_parser.add_argument("--baseline-run", required=True)
    compare_parser.add_argument("--candidate-run", required=True)
    compare_parser.add_argument("--qrels", required=True)
    compare_parser.add_argument(
        "--cutoff",
        required=True,
        type=_positive_integer_parser("cutoff"),
    )
    compare_parser.add_argument(
        "--metric",
        choices=SUPPORTED_COMPARISON_METRICS,
        default=NDCG_AT_K_METRIC,
    )
    compare_parser.add_argument(
        "--alternative",
        choices=SUPPORTED_COMPARISON_ALTERNATIVES,
        default=TWO_SIDED_ALTERNATIVE,
    )
    compare_parser.add_argument(
        "--randomizations",
        type=_positive_integer_parser("randomizations"),
        default=DEFAULT_RANDOMIZATION_COUNT,
    )
    compare_parser.add_argument(
        "--seed",
        type=_integer_seed,
        default=DEFAULT_RANDOM_SEED,
    )
    compare_parser.add_argument(
        "--max-input-bytes",
        type=_positive_integer_parser("max-input-bytes"),
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    compare_parser.add_argument(
        "--pretty",
        action="store_true",
        help="indent JSON output with two spaces",
    )
    return parser


def read_text_bounded(path: str | Path, max_input_bytes: int) -> str:
    """Read one strict-UTF-8 file after pre-read and bounded read checks."""
    file_path = Path(path)
    pre_read_size = file_path.stat().st_size
    if pre_read_size > max_input_bytes:
        raise ValueError(
            f"{file_path}: exceeds max-input-bytes {max_input_bytes}"
        )
    with file_path.open("rb") as input_file:
        raw_bytes = input_file.read(max_input_bytes + 1)
    if len(raw_bytes) > max_input_bytes:
        raise ValueError(
            f"{file_path}: exceeds max-input-bytes {max_input_bytes}"
        )
    try:
        return raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{file_path}: must be valid UTF-8") from exc


def _rankweave_version() -> str:
    """Return the package version without creating an import-time cycle."""
    import rankweave

    return rankweave.__version__


def comparison_to_dict(report: TrecRunComparisonReport) -> dict[str, Any]:
    """Project a complete TREC comparison to the stable JSON v1 schema."""
    if not isinstance(report, TrecRunComparisonReport):
        raise ValueError("report must be TrecRunComparisonReport")
    comparison = report.comparison
    significance = comparison.significance
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "rankweave_version": _rankweave_version(),
        "baseline_run_id": report.baseline_run.run_id,
        "candidate_run_id": report.candidate_run.run_id,
        "cutoff": comparison.baseline.cutoff,
        "metric_name": significance.metric_name,
        "alternative": significance.alternative,
        "query_count": significance.query_count,
        "nonzero_difference_count": significance.nonzero_difference_count,
        "baseline_mean": significance.baseline_mean,
        "candidate_mean": significance.candidate_mean,
        "mean_difference": significance.mean_difference,
        "p_value": significance.p_value,
        "method": significance.method,
        "randomizations_evaluated": significance.randomizations_evaluated,
        "random_seed": significance.random_seed,
        "query_differences": [
            {
                "query_id": difference.query_id,
                "baseline_value": difference.baseline_value,
                "candidate_value": difference.candidate_value,
                "difference": difference.difference,
            }
            for difference in significance.query_differences
        ],
    }


def _run_compare(arguments: argparse.Namespace) -> dict[str, Any]:
    """Execute the compare subcommand and return its JSON-ready payload."""
    baseline_run_text = read_text_bounded(
        arguments.baseline_run,
        arguments.max_input_bytes,
    )
    candidate_run_text = read_text_bounded(
        arguments.candidate_run,
        arguments.max_input_bytes,
    )
    qrels_text = read_text_bounded(
        arguments.qrels,
        arguments.max_input_bytes,
    )
    report = compare_trec_runs(
        baseline_run_text,
        candidate_run_text,
        qrels_text,
        cutoff=arguments.cutoff,
        metric_name=arguments.metric,
        alternative=arguments.alternative,
        randomization_count=arguments.randomizations,
        random_seed=arguments.seed,
    )
    return comparison_to_dict(report)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the RankWeave CLI and return its process exit status."""
    try:
        arguments = build_parser().parse_args(argv)
        payload = _run_compare(arguments)
        if arguments.pretty:
            rendered_output = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
        else:
            rendered_output = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
    except (_UsageError, OSError, ValueError) as exc:
        print(f"rankweave: error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(rendered_output)
    sys.stdout.write("\n")
    return 0
