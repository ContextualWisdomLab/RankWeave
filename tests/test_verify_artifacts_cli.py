import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rankweave.cli import VERIFICATION_OUTPUT_SCHEMA_VERSION, main

BASELINE_TEXT = (
    "q Q0 irrelevant 1 0.9 baseline\n"
    "q Q0 relevant 2 0.2 baseline\n"
)
CANDIDATE_TEXT = (
    "q Q0 relevant 1 0.9 candidate\n"
    "q Q0 irrelevant 2 0.2 candidate\n"
)
SECOND_CANDIDATE_TEXT = (
    "q Q0 relevant 1 0.95 candidate-b\n"
    "q Q0 irrelevant 2 0.10 candidate-b\n"
)
QRELS_TEXT = "q 0 relevant 1\nq 0 irrelevant 0\n"


def _write_artifacts(tmp_path):
    private_path = tmp_path / "private-inputs"
    private_path.mkdir()
    baseline_path = private_path / "baseline.run"
    candidate_path = private_path / "candidate.run"
    second_candidate_path = private_path / "candidate-b.run"
    qrels_path = private_path / "qrels.txt"
    baseline_path.write_text(BASELINE_TEXT, encoding="utf-8")
    candidate_path.write_text(CANDIDATE_TEXT, encoding="utf-8")
    second_candidate_path.write_text(SECOND_CANDIDATE_TEXT, encoding="utf-8")
    qrels_path.write_text(QRELS_TEXT, encoding="utf-8")
    return baseline_path, candidate_path, second_candidate_path, qrels_path


def _generate_pairwise_report(tmp_path, capsys):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)
    assert (
        main(
            [
                "compare",
                "--baseline-run",
                str(baseline_path),
                "--candidate-run",
                str(candidate_path),
                "--qrels",
                str(qrels_path),
                "--cutoff",
                "1",
                "--include-artifact-digests",
            ]
        )
        == 0
    )
    report_text = capsys.readouterr().out
    report_path = tmp_path / "pairwise-report.json"
    report_path.write_text(report_text, encoding="utf-8")
    return report_path, baseline_path, candidate_path, qrels_path


def _generate_family_report(tmp_path, capsys):
    baseline_path, candidate_path, second_candidate_path, qrels_path = (
        _write_artifacts(tmp_path)
    )
    assert (
        main(
            [
                "compare-family",
                "--baseline-run",
                str(baseline_path),
                "--candidate",
                f"first={candidate_path}",
                "--candidate",
                f"second={second_candidate_path}",
                "--qrels",
                str(qrels_path),
                "--cutoff",
                "1",
                "--include-artifact-digests",
            ]
        )
        == 0
    )
    report_text = capsys.readouterr().out
    report_path = tmp_path / "family-report.json"
    report_path.write_text(report_text, encoding="utf-8")
    return (
        report_path,
        baseline_path,
        candidate_path,
        second_candidate_path,
        qrels_path,
    )


def test_pairwise_verification_success_is_path_free_json(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert list(payload) == [
        "schema_version",
        "rankweave_version",
        "report_schema_version",
        "verified",
        "artifact_count",
        "mismatch_count",
        "artifacts",
    ]
    assert payload["schema_version"] == VERIFICATION_OUTPUT_SCHEMA_VERSION
    assert payload["rankweave_version"] == "0.16.0"
    assert payload["report_schema_version"] == "rankweave.trec-comparison.v2"
    assert payload["verified"] is True
    assert payload["artifact_count"] == 3
    assert payload["mismatch_count"] == 0
    assert [artifact["artifact_role"] for artifact in payload["artifacts"]] == [
        "baseline_run",
        "candidate_run",
        "qrels",
    ]
    assert all(artifact["candidate_id"] is None for artifact in payload["artifacts"])
    assert all(artifact["verified"] for artifact in payload["artifacts"])
    assert str(tmp_path) not in captured.out


def test_pairwise_mismatch_emits_json_and_exit_one(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )
    candidate_path.write_bytes(b"\xffchanged-binary-bytes")

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["verified"] is False
    assert payload["mismatch_count"] == 1
    candidate = payload["artifacts"][1]
    assert candidate["sha256_matches"] is False
    assert candidate["byte_count_matches"] is False
    assert candidate["verified"] is False
    assert str(candidate_path) not in captured.out


def test_family_verification_preserves_explicit_candidate_order(tmp_path, capsys):
    (
        report_path,
        baseline_path,
        candidate_path,
        second_candidate_path,
        qrels_path,
    ) = _generate_family_report(tmp_path, capsys)

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"first={candidate_path}",
            "--candidate",
            f"second={second_candidate_path}",
            "--qrels",
            str(qrels_path),
            "--pretty",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{\n  \"schema_version\"")
    assert payload["report_schema_version"] == (
        "rankweave.trec-family-comparison.v2"
    )
    assert payload["artifact_count"] == 4
    assert [
        (artifact["artifact_role"], artifact["candidate_id"])
        for artifact in payload["artifacts"]
    ] == [
        ("baseline_run", None),
        ("qrels", None),
        ("candidate_run", "first"),
        ("candidate_run", "second"),
    ]


def test_family_reordered_candidates_fail_as_usage_error(tmp_path, capsys):
    (
        report_path,
        baseline_path,
        candidate_path,
        second_candidate_path,
        qrels_path,
    ) = _generate_family_report(tmp_path, capsys)

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"second={second_candidate_path}",
            "--candidate",
            f"first={candidate_path}",
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "supplied candidate identifiers must match report order" in captured.err


@pytest.mark.parametrize(
    ("report_content", "message"),
    [
        ("not-json", "Expecting value"),
        (
            json.dumps(
                {
                    "schema_version": "rankweave.trec-comparison.v1",
                    "artifacts": {},
                }
            ),
            "supported v2 report schema",
        ),
        (json.dumps([]), "report must be a mapping"),
    ],
)
def test_invalid_report_content_is_stderr_only_exit_two(
    tmp_path, capsys, report_content, message
):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)
    report_path = tmp_path / "report.json"
    report_path.write_text(report_content, encoding="utf-8")

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert message in captured.err


def test_report_must_be_strict_utf8(tmp_path, capsys):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)
    report_path = tmp_path / "report.json"
    report_path.write_bytes(b"\xff")

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "must be valid UTF-8" in captured.err


def test_report_and_artifacts_share_the_bounded_read_contract(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
            "--max-input-bytes",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "exceeds max-input-bytes 1" in captured.err


def test_pairwise_report_rejects_family_candidate_options(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(report_path),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--candidate",
            f"first={candidate_path}",
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "candidate_run_bytes_by_id must be omitted" in captured.err


def test_module_entrypoint_matches_console_under_ascii_locale(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )
    arguments = [
        "verify-artifacts",
        "--report",
        str(report_path),
        "--baseline-run",
        str(baseline_path),
        "--candidate-run",
        str(candidate_path),
        "--qrels",
        str(qrels_path),
    ]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii:strict"

    console = subprocess.run(
        [
            sys.executable,
            "-c",
            "from rankweave.cli import main; raise SystemExit(main())",
            *arguments,
        ],
        check=False,
        capture_output=True,
        env=environment,
    )
    module = subprocess.run(
        [sys.executable, "-m", "rankweave", *arguments],
        check=False,
        capture_output=True,
        env=environment,
    )

    assert console.returncode == module.returncode == 0
    assert console.stderr == module.stderr == b""
    assert console.stdout == module.stdout
    payload = json.loads(module.stdout.decode("utf-8"))
    assert payload["schema_version"] == VERIFICATION_OUTPUT_SCHEMA_VERSION


def test_missing_report_file_is_stderr_only(tmp_path, capsys):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)

    exit_code = main(
        [
            "verify-artifacts",
            "--report",
            str(tmp_path / "missing.json"),
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "missing.json" in captured.err


def test_verification_output_contains_no_report_or_artifact_payloads(tmp_path, capsys):
    report_path, baseline_path, candidate_path, qrels_path = (
        _generate_pairwise_report(tmp_path, capsys)
    )

    assert (
        main(
            [
                "verify-artifacts",
                "--report",
                str(report_path),
                "--baseline-run",
                str(baseline_path),
                "--candidate-run",
                str(candidate_path),
                "--qrels",
                str(qrels_path),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out

    assert BASELINE_TEXT not in output
    assert CANDIDATE_TEXT not in output
    assert QRELS_TEXT not in output
    assert Path(report_path).name not in output
