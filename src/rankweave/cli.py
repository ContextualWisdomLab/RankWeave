"""Dependency-free command-line interface for auditable TREC comparisons."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    CANDIDATE_LESS_ALTERNATIVE,
    SUPPORTED_ALTERNATIVES,
    TWO_SIDED_ALTERNATIVE,
)
from .trec_comparison import TrecRunComparisonReport, compare_trec_runs
from .trec_family_comparison import (
    TrecRunFamilyComparisonReport,
    compare_trec_run_family,
)

OUTPUT_SCHEMA_VERSION = "rankweave.trec-comparison.v1"
FAMILY_OUTPUT_SCHEMA_VERSION = "rankweave.trec-family-comparison.v1"
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
_SUPPORTED_METRICS = (
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank_at_k",
    "ndcg_at_k",
)


def _positive_integer_parser(value: str) -> int:
    """Parse one positive integer for ``argparse``."""
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _integer_seed(value: str) -> int:
    """Parse one deterministic random seed for ``argparse``."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc


def _familywise_alpha_parser(value: str) -> float:
    """Parse a finite family-wise alpha value in ``(0, 1]``."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            "familywise-alpha must be a number"
        ) from exc
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("familywise-alpha must be finite")
    if not 0.0 < parsed <= 1.0:
        raise argparse.ArgumentTypeError("familywise-alpha must be in (0, 1]")
    return parsed


def _read_text_bounded(path: Path, *, max_bytes: int) -> str:
    """Read one strict UTF-8 artifact without exceeding the configured bound."""
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise ValueError("max-input-bytes must be a positive integer")
    try:
        file_size = path.stat().st_size
    except (OSError, ValueError) as exc:
        raise ValueError(f"unable to inspect {path}: {exc}") from exc
    if file_size > max_bytes:
        raise ValueError(
            f"artifact {path} is {file_size} bytes; exceeds max-input-bytes "
            f"{max_bytes}"
        )
    try:
        with path.open("rb") as artifact_file:
            try:
                payload = artifact_file.read(max_bytes + 1)
            except (OverflowError, ValueError) as exc:
                raise ValueError(
                    "max-input-bytes is too large for this platform's binary read API"
                ) from exc
    except OSError as exc:
        raise ValueError(f"unable to read {path}: {exc}") from exc
    if len(payload) > max_bytes:
        raise ValueError(
            f"artifact {path} exceeds max-input-bytes {max_bytes} while being read"
        )
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"artifact {path} is not valid UTF-8") from exc


def parse_candidate_specifications(
    specifications: Sequence[str],
) -> dict[str, str]:
    """Parse ordered repeatable ``ID=PATH`` candidate specifications."""
    if not specifications:
        raise ValueError("at least one --candidate ID=PATH is required")
    candidates: dict[str, str] = {}
    for specification in specifications:
        if "=" not in specification:
            raise ValueError("candidate must use ID=PATH syntax")
        candidate_id, path_text = specification.split("=", 1)
        if not candidate_id:
            raise ValueError("candidate identifier must not be empty")
        if candidate_id != candidate_id.strip():
            raise ValueError(
                "candidate identifier must not have leading or trailing whitespace"
            )
        if not all(character.isprintable() for character in candidate_id):
            raise ValueError("candidate identifier must contain printable characters")
        if not path_text:
            raise ValueError("candidate path must not be empty")
        if candidate_id in candidates:
            raise ValueError(f"duplicate candidate identifier {candidate_id!r}")
        candidates[candidate_id] = path_text
    return candidates


def _macro_metric_value(aggregate: object, metric_name: str) -> float:
    """Return one aggregate metric from an immutable evaluation report."""
    attribute = {
        "precision_at_k": "mean_precision_at_k",
        "recall_at_k": "mean_recall_at_k",
        "reciprocal_rank_at_k": "mean_reciprocal_rank_at_k",
        "ndcg_at_k": "mean_ndcg_at_k",
    }[metric_name]
    return float(getattr(aggregate, attribute))


def _query_difference_to_dict(difference: object) -> dict[str, Any]:
    """Project one immutable per-query difference to JSON-compatible data."""
    return {
        "query_id": getattr(difference, "query_id"),
        "baseline_value": getattr(difference, "baseline_value"),
        "candidate_value": getattr(difference, "candidate_value"),
        "difference": getattr(difference, "difference"),
    }


def comparison_report_to_dict(report: TrecRunComparisonReport) -> dict[str, Any]:
    """Project one comparison report into the stable CLI output schema."""
    if not isinstance(report, TrecRunComparisonReport):
        raise ValueError("report must be a TrecRunComparisonReport")
    significance = report.comparison.significance
    metric_name = significance.metric_name
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "rankweave_version": __version__,
        "baseline_run_id": report.baseline_run.run_id,
        "candidate_run_id": report.candidate_run.run_id,
        "cutoff": report.comparison.baseline.cutoff,
        "metric_name": metric_name,
        "alternative": significance.alternative,
        "query_count": significance.query_count,
        "nonzero_difference_count": significance.nonzero_difference_count,
        "baseline_mean": _macro_metric_value(
            report.comparison.baseline.aggregate,
            metric_name,
        ),
        "candidate_mean": _macro_metric_value(
            report.comparison.candidate.aggregate,
            metric_name,
        ),
        "mean_difference": significance.mean_difference,
        "p_value": significance.p_value,
        "method": significance.method,
        "randomizations_evaluated": significance.randomizations_evaluated,
        "random_seed": significance.random_seed,
        "query_differences": [
            _query_difference_to_dict(difference)
            for difference in significance.query_differences
        ],
    }


def family_comparison_to_dict(
    report: TrecRunFamilyComparisonReport,
) -> dict[str, Any]:
    """Project one family report into the stable family CLI output schema."""
    if not isinstance(report, TrecRunFamilyComparisonReport):
        raise ValueError("report must be a TrecRunFamilyComparisonReport")
    first_significance = report.candidates[0].comparison.significance
    candidates = []
    for candidate in report.candidates:
        if not isinstance(candidate.candidate_id, str):
            raise ValueError("family comparison candidate identifiers must be strings")
        comparison = candidate.comparison
        significance = comparison.significance
        metric_name = significance.metric_name
        candidates.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_run_id": candidate.candidate_run.run_id,
                "query_count": significance.query_count,
                "nonzero_difference_count": significance.nonzero_difference_count,
                "baseline_mean": _macro_metric_value(
                    comparison.baseline.aggregate,
                    metric_name,
                ),
                "candidate_mean": _macro_metric_value(
                    comparison.candidate.aggregate,
                    metric_name,
                ),
                "mean_difference": significance.mean_difference,
                "raw_p_value": candidate.raw_p_value,
                "holm_adjusted_p_value": candidate.holm_adjusted_p_value,
                "rejected_at_familywise_alpha": (
                    candidate.rejected_at_familywise_alpha
                ),
                "method": significance.method,
                "randomizations_evaluated": (
                    significance.randomizations_evaluated
                ),
                "random_seed": significance.random_seed,
                "query_differences": [
                    _query_difference_to_dict(difference)
                    for difference in significance.query_differences
                ],
            }
        )
    return {
        "schema_version": FAMILY_OUTPUT_SCHEMA_VERSION,
        "rankweave_version": __version__,
        "baseline_run_id": report.baseline_run.run_id,
        "cutoff": report.baseline_evaluation.cutoff,
        "metric_name": first_significance.metric_name,
        "alternative": first_significance.alternative,
        "familywise_alpha": report.familywise_alpha,
        "candidate_count": len(report.candidates),
        "candidates": candidates,
    }


def _add_shared_comparison_arguments(parser: argparse.ArgumentParser) -> None:
    """Add options shared by pairwise and candidate-family comparisons."""
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--qrels", required=True, type=Path)
    parser.add_argument("--cutoff", required=True, type=_positive_integer_parser)
    parser.add_argument("--metric", choices=_SUPPORTED_METRICS, default="ndcg_at_k")
    parser.add_argument(
        "--alternative",
        choices=SUPPORTED_ALTERNATIVES,
        default=TWO_SIDED_ALTERNATIVE,
        help=(
            f"{TWO_SIDED_ALTERNATIVE}, {CANDIDATE_GREATER_ALTERNATIVE}, or "
            f"{CANDIDATE_LESS_ALTERNATIVE}"
        ),
    )
    parser.add_argument(
        "--randomizations",
        type=_positive_integer_parser,
        default=10_000,
    )
    parser.add_argument("--seed", type=_integer_seed, default=0)
    parser.add_argument(
        "--max-input-bytes",
        type=_positive_integer_parser,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument("--pretty", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    """Build the installed ``rankweave`` command-line parser."""
    parser = argparse.ArgumentParser(
        prog="rankweave",
        description="Auditable retrieval-fusion and TREC comparison workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare one baseline and candidate TREC run against one qrels file.",
    )
    _add_shared_comparison_arguments(compare_parser)
    compare_parser.add_argument("--candidate-run", required=True, type=Path)

    family_parser = subparsers.add_parser(
        "compare-family",
        help="Compare an ordered candidate family with Holm correction.",
    )
    _add_shared_comparison_arguments(family_parser)
    family_parser.add_argument(
        "--candidate",
        dest="candidate_specs",
        action="append",
        required=True,
        metavar="ID=PATH",
        help="Repeat for each explicitly named candidate run, in family order.",
    )
    family_parser.add_argument(
        "--familywise-alpha",
        type=_familywise_alpha_parser,
        default=0.05,
    )
    return parser


def _write_json(payload: Mapping[str, Any], *, pretty: bool) -> None:
    """Write one deterministic UTF-8 JSON document to standard output."""
    if pretty:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    else:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    sys.stdout.write(serialized)
    sys.stdout.write("\n")


def _run_compare(arguments: argparse.Namespace) -> None:
    """Run one pairwise TREC comparison from parsed command arguments."""
    max_bytes = arguments.max_input_bytes
    baseline_text = _read_text_bounded(arguments.baseline_run, max_bytes=max_bytes)
    candidate_text = _read_text_bounded(arguments.candidate_run, max_bytes=max_bytes)
    qrels_text = _read_text_bounded(arguments.qrels, max_bytes=max_bytes)
    report = compare_trec_runs(
        baseline_text,
        candidate_text,
        qrels_text,
        cutoff=arguments.cutoff,
        metric_name=arguments.metric,
        alternative=arguments.alternative,
        randomization_count=arguments.randomizations,
        random_seed=arguments.seed,
    )
    _write_json(comparison_report_to_dict(report), pretty=arguments.pretty)


def _run_compare_family(arguments: argparse.Namespace) -> None:
    """Run one TREC candidate-family comparison from parsed arguments."""
    candidate_paths = parse_candidate_specifications(arguments.candidate_specs)
    max_bytes = arguments.max_input_bytes
    baseline_text = _read_text_bounded(arguments.baseline_run, max_bytes=max_bytes)
    candidate_texts = {
        candidate_id: _read_text_bounded(Path(path_text), max_bytes=max_bytes)
        for candidate_id, path_text in candidate_paths.items()
    }
    qrels_text = _read_text_bounded(arguments.qrels, max_bytes=max_bytes)
    report = compare_trec_run_family(
        baseline_text,
        candidate_texts,
        qrels_text,
        cutoff=arguments.cutoff,
        metric_name=arguments.metric,
        alternative=arguments.alternative,
        randomization_count=arguments.randomizations,
        random_seed=arguments.seed,
        familywise_alpha=arguments.familywise_alpha,
    )
    _write_json(family_comparison_to_dict(report), pretty=arguments.pretty)


def main(argv: list[str] | None = None) -> int:
    """Execute the CLI and return a stable process exit code."""
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
        if arguments.command == "compare":
            _run_compare(arguments)
        elif arguments.command == "compare-family":
            _run_compare_family(arguments)
        else:  # pragma: no cover - argparse restricts this branch.
            raise ValueError(f"unsupported command {arguments.command!r}")
    except (OSError, TypeError, ValueError, argparse.ArgumentError) as exc:
        sys.stderr.write(f"rankweave: error: {exc}\n")
        return 2
    return 0
