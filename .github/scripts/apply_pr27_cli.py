"""Apply the reviewed RankWeave artifact-verification CLI patch."""

from __future__ import annotations

from pathlib import Path


def insert_before(text: str, marker: str, addition: str, label: str) -> str:
    """Insert text once before an exact marker."""
    if marker not in text:
        raise SystemExit(f"missing insertion marker: {label}")
    return text.replace(marker, addition + marker, 1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one exact source fragment."""
    if old not in text:
        raise SystemExit(f"missing replacement marker: {label}")
    return text.replace(old, new, 1)


def patch_cli() -> None:
    """Implement the bounded verification command and transport projection."""
    path = Path("src/rankweave/cli.py")
    text = path.read_text(encoding="utf-8")

    if "from rankweave.artifact_verification import (" not in text:
        text = insert_before(
            text,
            "from rankweave.comparison import (\n",
            "from rankweave.artifact_verification import (\n"
            "    ArtifactVerificationReport,\n"
            "    verify_report_artifacts,\n"
            ")\n",
            "artifact imports",
        )
    if "VERIFICATION_OUTPUT_SCHEMA_VERSION" not in text:
        text = replace_once(
            text,
            'FAMILY_OUTPUT_SCHEMA_VERSION_V2 = '
            '"rankweave.trec-family-comparison.v2"\n',
            'FAMILY_OUTPUT_SCHEMA_VERSION_V2 = '
            '"rankweave.trec-family-comparison.v2"\n'
            'VERIFICATION_OUTPUT_SCHEMA_VERSION = '
            '"rankweave.artifact-verification.v1"\n',
            "verification schema constant",
        )

    if '        "verify-artifacts",\n' not in text:
        parser_block = '''    verification_parser = subcommands.add_parser(
        "verify-artifacts",
        help="verify local artifacts against one persisted v2 report",
    )
    verification_parser.add_argument("--report", required=True)
    verification_parser.add_argument("--baseline-run", required=True)
    verification_parser.add_argument("--qrels", required=True)
    verification_parser.add_argument("--candidate-run")
    verification_parser.add_argument(
        "--candidate",
        dest="candidate_specs",
        action="append",
        metavar="ID=PATH",
    )
    verification_parser.add_argument(
        "--max-input-bytes",
        type=_positive_integer_parser("max-input-bytes"),
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    verification_parser.add_argument(
        "--pretty",
        action="store_true",
        help="indent JSON output with two spaces",
    )

'''
        text = insert_before(
            text,
            "    schema_parser = subcommands.add_parser(\n",
            parser_block,
            "verification parser",
        )

    if "def _read_bytes_bounded(" not in text:
        start = text.index("def _read_text_artifact_bounded(")
        end = text.index("\n\ndef read_text_bounded(", start)
        replacement = '''def _read_bytes_bounded(
    path: str | Path,
    max_input_bytes: int,
) -> bytes:
    """Read one local file within the observed and actual byte ceiling."""
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
        raise ValueError(
            "max_input_bytes is too large for this platform"
        ) from exc
    if len(raw_bytes) > max_input_bytes:
        raise ValueError(
            f"{file_path}: exceeds max-input-bytes {max_input_bytes}"
        )
    return raw_bytes


def _read_text_artifact_bounded(
    path: str | Path,
    max_input_bytes: int,
) -> _BoundedTextArtifact:
    """Read, hash, count, and strictly decode one bounded local artifact."""
    file_path = Path(path)
    raw_bytes = _read_bytes_bounded(file_path, max_input_bytes)
    try:
        decoded_text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{file_path}: must be valid UTF-8") from exc
    return _BoundedTextArtifact(
        text=decoded_text,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        byte_count=len(raw_bytes),
    )
'''
        text = text[:start] + replacement + text[end:]

    if "def artifact_verification_to_dict(" not in text:
        projection = '''def artifact_verification_to_dict(
    report: ArtifactVerificationReport,
) -> dict[str, Any]:
    """Project one immutable verification result to stable JSON data."""
    if not isinstance(report, ArtifactVerificationReport):
        raise ValueError("report must be ArtifactVerificationReport")
    return {
        "schema_version": VERIFICATION_OUTPUT_SCHEMA_VERSION,
        "rankweave_version": _rankweave_version(),
        "report_schema_version": report.report_schema_version,
        "verified": report.verified,
        "artifact_count": len(report.artifacts),
        "mismatch_count": report.mismatch_count,
        "artifacts": [
            {
                "artifact_role": artifact.artifact_role,
                "candidate_id": artifact.candidate_id,
                "expected_sha256": artifact.expected_sha256,
                "actual_sha256": artifact.actual_sha256,
                "sha256_matches": artifact.sha256_matches,
                "expected_byte_count": artifact.expected_byte_count,
                "actual_byte_count": artifact.actual_byte_count,
                "byte_count_matches": artifact.byte_count_matches,
                "verified": artifact.verified,
            }
            for artifact in report.artifacts
        ],
    }


'''
        text = insert_before(
            text,
            "def _run_compare(arguments: argparse.Namespace) -> dict[str, Any]:\n",
            projection,
            "verification projection",
        )

    if "def _run_verify_artifacts(" not in text:
        runner = '''def _run_verify_artifacts(
    arguments: argparse.Namespace,
) -> ArtifactVerificationReport:
    """Verify bounded local artifacts against one persisted v2 report."""
    report_artifact = _read_text_artifact_bounded(
        arguments.report,
        arguments.max_input_bytes,
    )
    report_data = json.loads(report_artifact.text)
    baseline_run_bytes = _read_bytes_bounded(
        arguments.baseline_run,
        arguments.max_input_bytes,
    )
    qrels_bytes = _read_bytes_bounded(
        arguments.qrels,
        arguments.max_input_bytes,
    )
    candidate_run_bytes = (
        None
        if arguments.candidate_run is None
        else _read_bytes_bounded(
            arguments.candidate_run,
            arguments.max_input_bytes,
        )
    )
    candidate_run_bytes_by_id = None
    if arguments.candidate_specs is not None:
        candidate_paths = parse_candidate_specifications(arguments.candidate_specs)
        candidate_run_bytes_by_id = {
            candidate_id: _read_bytes_bounded(
                candidate_path,
                arguments.max_input_bytes,
            )
            for candidate_id, candidate_path in candidate_paths.items()
        }
    return verify_report_artifacts(
        report_data,
        baseline_run_bytes=baseline_run_bytes,
        candidate_run_bytes=candidate_run_bytes,
        qrels_bytes=qrels_bytes,
        candidate_run_bytes_by_id=candidate_run_bytes_by_id,
    )


'''
        text = insert_before(
            text,
            "def main(argv: Sequence[str] | None = None) -> int:\n",
            runner,
            "verification runner",
        )

    main_start = text.index("def main(argv: Sequence[str] | None = None) -> int:")
    new_main = '''def main(argv: Sequence[str] | None = None) -> int:
    """Run the RankWeave CLI and return its process exit status."""
    exit_status = 0
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
            elif arguments.command == "compare-family":
                payload = _run_compare_family(arguments)
            else:
                verification = _run_verify_artifacts(arguments)
                payload = artifact_verification_to_dict(verification)
                exit_status = 0 if verification.verified else 1
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
    return exit_status
'''
    text = text[:main_start] + new_main
    path.write_text(text, encoding="utf-8")


def patch_public_api() -> None:
    """Expose verification records and synchronize the release version."""
    path = Path("src/rankweave/__init__.py")
    text = path.read_text(encoding="utf-8")
    if "from rankweave.artifact_verification import (" not in text:
        text = insert_before(
            text,
            "from rankweave.comparison import (\n",
            "from rankweave.artifact_verification import (\n"
            "    FAMILY_REPORT_SCHEMA_VERSION,\n"
            "    PAIRWISE_REPORT_SCHEMA_VERSION,\n"
            "    ArtifactVerificationRecord,\n"
            "    ArtifactVerificationReport,\n"
            "    verify_report_artifacts,\n"
            ")\n",
            "public artifact imports",
        )
    text = replace_once(
        text,
        '__version__ = "0.13.0"',
        '__version__ = "0.14.0"',
        "public version",
    )
    text = replace_once(
        text,
        '    "AggregateRankingMetrics",\n',
        '    "AggregateRankingMetrics",\n'
        '    "ArtifactVerificationRecord",\n'
        '    "ArtifactVerificationReport",\n',
        "verification records",
    )
    text = replace_once(
        text,
        '    "FusedRankedItem",\n',
        '    "FAMILY_REPORT_SCHEMA_VERSION",\n'
        '    "FusedRankedItem",\n',
        "family report constant",
    )
    text = replace_once(
        text,
        '    "PRECISION_AT_K_METRIC",\n',
        '    "PAIRWISE_REPORT_SCHEMA_VERSION",\n'
        '    "PRECISION_AT_K_METRIC",\n',
        "pairwise report constant",
    )
    text = replace_once(
        text,
        '    "weighted_reciprocal_rank_fusion_score",\n',
        '    "verify_report_artifacts",\n'
        '    "weighted_reciprocal_rank_fusion_score",\n',
        "verification function",
    )
    path.write_text(text, encoding="utf-8")

    replacements = (
        ("pyproject.toml", 'version = "0.13.0"', 'version = "0.14.0"'),
        (
            "tests/test_version.py",
            'EXPECTED_RELEASE_VERSION = "0.13.0"',
            'EXPECTED_RELEASE_VERSION = "0.14.0"',
        ),
    )
    for path_text, old, new in replacements:
        file_path = Path(path_text)
        value = file_path.read_text(encoding="utf-8")
        if old not in value:
            raise SystemExit(f"missing version marker: {path_text}")
        file_path.write_text(value.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    """Apply all deterministic PR 27 CLI source changes."""
    patch_cli()
    patch_public_api()


if __name__ == "__main__":
    main()
