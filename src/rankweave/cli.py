"""Command-line adapter for strict TREC retrieval-system comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rankweave.comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    CANDIDATE_LESS_ALTERNATIVE,
    DEFAULT_RANDOM_SEED,
    DEFAULT_RANDOMIZATION_COUNT,
    NDCG_AT_K_METRIC,
    SUPPORTED_COMPARISON_ALTERNATIVES,
    SUPPORTED_COMPARISON_METRICS,
    TWO_SIDED_ALTERNATIVE,
    QueryMetricDifference,
)
from rankweave.report_schemas import load_report_schema_text
from rankweave.trec_comparison import (
    TrecRunComparisonReport,
    compare_trec_runs,
)
from rankweave.trec_family_comparison import (
    TrecRunFamilyComparisonReport,
    compare_trec_run_family,
)

OUTPUT_SCHEMA_VERSION = "rankweave.trec-comparison.v1"
OUTPUT_SCHEMA_VERSION_V2 = "rankweave.trec-comparison.v2"
FAMILY_OUTPUT_SCHEMA_VERSION = "rankweave.trec-family-comparison.v1"
FAMILY_OUTPUT_SCHEMA_VERSION_V2 = "rankweave.trec-family-comparison.v2"
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
_SIGNED_DECIMAL_PATTERN = re.compile(r"[+-]?[0-9]+")


@dataclass(frozen=True)
class _BoundedTextArtifact:
    """One strictly decoded local artifact and its exact raw-byte evidence."""

    text: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class _PairwiseArtifactEvidence:
    """Exact input-artifact evidence for one pairwise comparison."""

    baseline_run: _BoundedTextArtifact
    candidate_run: _BoundedTextArtifact
    qrels: _BoundedTextArtifact


@dataclass(frozen=True)
class _NamedArtifactEvidence:
    """One explicit candidate identifier and its exact input evidence."""

    candidate_id: str
    artifact: _BoundedTextArtifact


@dataclass(frozen=True)
class _FamilyArtifactEvidence:
    """Exact ordered input evidence for one candidate-family comparison."""

    baseline_run: _BoundedTextArtifact
    qrels: _BoundedTextArtifact
    candidates: tuple[_NamedArtifactEvidence, ...]


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


def _familywise_alpha(raw_value: str) -> float:
    """Parse one finite family-wise alpha value in ``(0, 1]``."""
    try:
        parsed_value = float(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "familywise-alpha must be a number"
        ) from exc
    if not math.isfinite(parsed_value):
        raise argparse.ArgumentTypeError("familywise-alpha must be finite")
    if not 0.0 < parsed_value <= 1.0:
        raise argparse.ArgumentTypeError(
            "familywise-alpha must be in (0, 1]"
        )
    return parsed_value


def _add_shared_comparison_arguments(parser: argparse.ArgumentParser) -> None:
    """Add options shared by pairwise and candidate-family comparisons."""
    parser.add_argument("--baseline-run", required=True)
    parser.add_argument("--qrels", required=True)
    parser.add_argument(
        "--cutoff",
        required=True,
        type=_positive_integer_parser("cutoff"),
    )
    parser.add_argument(
        "--metric",
        choices=SUPPORTED_COMPARISON_METRICS,
        default=NDCG_AT_K_METRIC,
    )
    parser.add_argument(
        "--alternative",
        choices=SUPPORTED_COMPARISON_ALTERNATIVES,
        default=TWO_SIDED_ALTERNATIVE,
        help=(
            f"{TWO_SIDED_ALTERNATIVE}, {CANDIDATE_GREATER_ALTERNATIVE}, or "
            f"{CANDIDATE_LESS_ALTERNATIVE}"
        ),
    )
    parser.add_argument(
        "--randomizations",
        type=_positive_integer_parser("randomizations"),
        default=DEFAULT_RANDOMIZATION_COUNT,
    )
    parser.add_argument(
        "--seed",
        type=_integer_seed,
        default=DEFAULT_RANDOM_SEED,
    )
    parser.add_argument(
        "--max-input-bytes",
        type=_positive_integer_parser("max-input-bytes"),
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="indent JSON output with two spaces",
    )
    parser.add_argument(
        "--include-artifact-digests",
        action="store_true",
        help="emit v2 JSON with SHA-256 and exact byte counts for every input",
    )


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
    _add_shared_comparison_arguments(compare_parser)
    compare_parser.add_argument("--candidate-run", required=True)

    family_parser = subcommands.add_parser(
        "compare-family",
        help="compare an ordered TREC candidate family with Holm correction",
    )
    _add_shared_comparison_arguments(family_parser)
    family_parser.add_argument(
        "--candidate",
        dest="candidate_specs",
        action="append",
        required=True,
        metavar="ID=PATH",
        help="repeat for each explicitly named candidate run in family order",
    )
    family_parser.add_argument(
        "--familywise-alpha",
        type=_familywise_alpha,
        default=0.05,
    )

    schema_parser = subcommands.add_parser(
        "schema",
        help="emit one packaged JSON Schema report contract",
    )
    schema_parser.add_argument(
        "--report-type",
        required=True,
        choices=("pairwise", "family"),
    )
    schema_parser.add_argument(
        "--schema-version",
        required=True,
        choices=("v1", "v2"),
    )
    return parser


def _read_text_artifact_bounded(
    path: str | Path,
    max_input_bytes: int,
) -> _BoundedTextArtifact:
    """Read, hash, count, and strictly decode one bounded local artifact."""
    file_path = Path(path)
    pre_read_size = file_path.stat().st_size
    if pre_read_size > max_input_bytes:
        raise ValueError(
            f"{file_path}: exceeds max-input-bytes {max_input_bytes}"
        )
    try:
        with file_path.open("rb") as input_file:
            raw_bytes = input_file.read(max_input_bytes + 1)
    except OverflowError as exc:
        raise ValueError("max_input_bytes is too large for this platform") from exc
    if len(raw_bytes) > max_input_bytes:
        raise ValueError(
            f"{file_path}: exceeds max-input-bytes {max_input_bytes}"
        )
    try:
        decoded_text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{file_path}: must be valid UTF-8") from exc
    return _BoundedTextArtifact(
        text=decoded_text,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        byte_count=len(raw_bytes),
    )


def read_text_bounded(path: str | Path, max_input_bytes: int) -> str:
    """Read one strict-UTF-8 file after pre-read and bounded read checks."""
    return _read_text_artifact_bounded(path, max_input_bytes).text


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


def _rankweave_version() -> str:
    """Return the package version without creating an import-time cycle."""
    import rankweave

    return rankweave.__version__


def _query_difference_to_dict(
    difference: QueryMetricDifference[Any],
) -> dict[str, Any]:
    """Project one immutable per-query difference to JSON-compatible data."""
    return {
        "query_id": difference.query_id,
        "baseline_value": difference.baseline_value,
        "candidate_value": difference.candidate_value,
        "difference": difference.difference,
    }


def _artifact_digest_to_dict(artifact: _BoundedTextArtifact) -> dict[str, Any]:
    """Project one bounded artifact to path-free digest evidence."""
    if not isinstance(artifact, _BoundedTextArtifact):
        raise ValueError("artifact evidence must be a bounded text artifact")
    return {
        "sha256": artifact.sha256,
        "byte_count": artifact.byte_count,
    }


def _pairwise_artifacts_to_dict(
    evidence: _PairwiseArtifactEvidence,
) -> dict[str, Any]:
    """Project pairwise artifact evidence in stable role order."""
    if not isinstance(evidence, _PairwiseArtifactEvidence):
        raise ValueError("pairwise artifact evidence has the wrong type")
    return {
        "baseline_run": _artifact_digest_to_dict(evidence.baseline_run),
        "candidate_run": _artifact_digest_to_dict(evidence.candidate_run),
        "qrels": _artifact_digest_to_dict(evidence.qrels),
    }


def _family_artifacts_to_dict(
    report: TrecRunFamilyComparisonReport[str],
    evidence: _FamilyArtifactEvidence,
) -> dict[str, Any]:
    """Project ordered family artifact evidence after identifier alignment."""
    if not isinstance(evidence, _FamilyArtifactEvidence):
        raise ValueError("family artifact evidence has the wrong type")
    expected_candidate_ids = tuple(
        candidate.candidate_id for candidate in report.candidates
    )
    evidence_candidate_ids = tuple(
        candidate.candidate_id for candidate in evidence.candidates
    )
    if evidence_candidate_ids != expected_candidate_ids:
        raise ValueError(
            "artifact evidence candidate identifiers must match report order"
        )
    return {
        "baseline_run": _artifact_digest_to_dict(evidence.baseline_run),
        "qrels": _artifact_digest_to_dict(evidence.qrels),
        "candidates": [
            {
                "candidate_id": candidate.candidate_id,
                **_artifact_digest_to_dict(candidate.artifact),
            }
            for candidate in evidence.candidates
        ],
    }


def comparison_to_dict(
    report: TrecRunComparisonReport,
    *,
    artifact_evidence: _PairwiseArtifactEvidence | None = None,
) -> dict[str, Any]:
    """Project a complete TREC comparison to a stable JSON schema."""
    if not isinstance(report, TrecRunComparisonReport):
        raise ValueError("report must be TrecRunComparisonReport")
    comparison = report.comparison
    significance = comparison.significance
    payload: dict[str, Any] = {
        "schema_version": (
            OUTPUT_SCHEMA_VERSION
            if artifact_evidence is None
            else OUTPUT_SCHEMA_VERSION_V2
        ),
        "rankweave_version": _rankweave_version(),
    }
    if artifact_evidence is not None:
        payload["artifacts"] = _pairwise_artifacts_to_dict(artifact_evidence)
    payload.update(
        {
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
                _query_difference_to_dict(difference)
                for difference in significance.query_differences
            ],
        }
    )
    return payload


def family_comparison_to_dict(
    report: TrecRunFamilyComparisonReport[str],
    *,
    artifact_evidence: _FamilyArtifactEvidence | None = None,
) -> dict[str, Any]:
    """Project a candidate-family comparison to a stable JSON schema."""
    if not isinstance(report, TrecRunFamilyComparisonReport):
        raise ValueError("report must be TrecRunFamilyComparisonReport")
    first_comparison = report.candidates[0].comparison
    candidates: list[dict[str, Any]] = []
    for candidate in report.candidates:
        if not isinstance(candidate.candidate_id, str):
            raise ValueError(
                "family comparison candidate identifiers must be strings"
            )
        significance = candidate.comparison.significance
        candidates.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_run_id": candidate.candidate_run.run_id,
                "query_count": significance.query_count,
                "nonzero_difference_count": (
                    significance.nonzero_difference_count
                ),
                "baseline_mean": significance.baseline_mean,
                "candidate_mean": significance.candidate_mean,
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
    payload: dict[str, Any] = {
        "schema_version": (
            FAMILY_OUTPUT_SCHEMA_VERSION
            if artifact_evidence is None
            else FAMILY_OUTPUT_SCHEMA_VERSION_V2
        ),
        "rankweave_version": _rankweave_version(),
    }
    if artifact_evidence is not None:
        payload["artifacts"] = _family_artifacts_to_dict(
            report,
            artifact_evidence,
        )
    payload.update(
        {
            "baseline_run_id": report.baseline_run.run_id,
            "cutoff": first_comparison.baseline.cutoff,
            "metric_name": report.metric_name,
            "alternative": report.alternative,
            "familywise_alpha": report.familywise_alpha,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
    )
    return payload


def _run_compare(arguments: argparse.Namespace) -> dict[str, Any]:
    """Execute the compare subcommand and return its JSON-ready payload."""
    baseline_run = _read_text_artifact_bounded(
        arguments.baseline_run,
        arguments.max_input_bytes,
    )
    candidate_run = _read_text_artifact_bounded(
        arguments.candidate_run,
        arguments.max_input_bytes,
    )
    qrels = _read_text_artifact_bounded(
        arguments.qrels,
        arguments.max_input_bytes,
    )
    report = compare_trec_runs(
        baseline_run.text,
        candidate_run.text,
        qrels.text,
        cutoff=arguments.cutoff,
        metric_name=arguments.metric,
        alternative=arguments.alternative,
        randomization_count=arguments.randomizations,
        random_seed=arguments.seed,
    )
    artifact_evidence = (
        _PairwiseArtifactEvidence(
            baseline_run=baseline_run,
            candidate_run=candidate_run,
            qrels=qrels,
        )
        if arguments.include_artifact_digests
        else None
    )
    return comparison_to_dict(report, artifact_evidence=artifact_evidence)


def _run_compare_family(arguments: argparse.Namespace) -> dict[str, Any]:
    """Execute compare-family and return its JSON-ready payload."""
    candidate_paths = parse_candidate_specifications(arguments.candidate_specs)
    baseline_run = _read_text_artifact_bounded(
        arguments.baseline_run,
        arguments.max_input_bytes,
    )
    candidate_runs = tuple(
        _NamedArtifactEvidence(
            candidate_id=candidate_id,
            artifact=_read_text_artifact_bounded(
                candidate_path,
                arguments.max_input_bytes,
            ),
        )
        for candidate_id, candidate_path in candidate_paths.items()
    )
    qrels = _read_text_artifact_bounded(
        arguments.qrels,
        arguments.max_input_bytes,
    )
    report = compare_trec_run_family(
        baseline_run.text,
        {
            candidate.candidate_id: candidate.artifact.text
            for candidate in candidate_runs
        },
        qrels.text,
        cutoff=arguments.cutoff,
        metric_name=arguments.metric,
        alternative=arguments.alternative,
        familywise_alpha=arguments.familywise_alpha,
        randomization_count=arguments.randomizations,
        random_seed=arguments.seed,
    )
    artifact_evidence = (
        _FamilyArtifactEvidence(
            baseline_run=baseline_run,
            qrels=qrels,
            candidates=candidate_runs,
        )
        if arguments.include_artifact_digests
        else None
    )
    return family_comparison_to_dict(
        report,
        artifact_evidence=artifact_evidence,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the RankWeave CLI and return its process exit status."""
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.command == "schema":
            output_bytes = load_report_schema_text(
                arguments.report_type,
                arguments.schema_version,
            ).encode("utf-8")
        else:
            if arguments.command == "compare":
                payload = _run_compare(arguments)
            else:
                payload = _run_compare_family(arguments)
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
            output_bytes = rendered_output.encode("utf-8") + b"\n"
    except (_UsageError, OSError, ValueError) as exc:
        print(f"rankweave: error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.buffer.write(output_bytes)
    return 0
