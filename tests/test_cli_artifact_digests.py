import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from rankweave.cli import (
    FAMILY_OUTPUT_SCHEMA_VERSION,
    FAMILY_OUTPUT_SCHEMA_VERSION_V2,
    OUTPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION_V2,
    _artifact_digest_to_dict,
    _BoundedTextArtifact,
    _family_artifacts_to_dict,
    _FamilyArtifactEvidence,
    _NamedArtifactEvidence,
    _pairwise_artifacts_to_dict,
    main,
)
from rankweave.trec_family_comparison import compare_trec_run_family

QRELS_BYTES = (
    "# 판단 근거\n"
    "query 0 relevant 1\n"
    "query 0 irrelevant 0\n"
).encode()
BASELINE_BYTES = (
    "# 기준 실행\n"
    "query Q0 irrelevant 1 0.9 baseline\n"
    "query Q0 relevant 2 0.2 baseline\n"
).encode()
CANDIDATE_BYTES = (
    "# 후보 실행\n"
    "query Q0 relevant 1 0.9 candidate\n"
    "query Q0 irrelevant 2 0.2 candidate\n"
).encode()
SECOND_CANDIDATE_BYTES = (
    "# 두 번째 후보\n"
    "query Q0 relevant 1 0.95 candidate-b\n"
    "query Q0 irrelevant 2 0.10 candidate-b\n"
).encode()


def _write_artifacts(tmp_path):
    baseline_path = tmp_path / "private" / "baseline.run"
    candidate_path = tmp_path / "private" / "candidate.run"
    second_candidate_path = tmp_path / "private" / "candidate-b.run"
    qrels_path = tmp_path / "private" / "qrels.txt"
    baseline_path.parent.mkdir()
    baseline_path.write_bytes(BASELINE_BYTES)
    candidate_path.write_bytes(CANDIDATE_BYTES)
    second_candidate_path.write_bytes(SECOND_CANDIDATE_BYTES)
    qrels_path.write_bytes(QRELS_BYTES)
    return baseline_path, candidate_path, second_candidate_path, qrels_path


def _digest(payload: bytes) -> dict[str, object]:
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
    }


def _empty_artifact() -> _BoundedTextArtifact:
    return _BoundedTextArtifact(text="", sha256="0" * 64, byte_count=0)


def test_pairwise_digest_mode_binds_exact_input_bytes_without_paths(tmp_path, capsys):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)

    exit_code = main(
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
            "--alternative",
            "candidate-greater",
            "--include-artifact-digests",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["schema_version"] == OUTPUT_SCHEMA_VERSION_V2
    assert list(payload)[:3] == [
        "schema_version",
        "rankweave_version",
        "artifacts",
    ]
    assert payload["artifacts"] == {
        "baseline_run": _digest(BASELINE_BYTES),
        "candidate_run": _digest(CANDIDATE_BYTES),
        "qrels": _digest(QRELS_BYTES),
    }
    assert str(tmp_path) not in captured.out


def test_family_digest_mode_preserves_candidate_order_and_byte_counts(
    tmp_path, capsys
):
    baseline_path, candidate_path, second_candidate_path, qrels_path = (
        _write_artifacts(tmp_path)
    )

    exit_code = main(
        [
            "compare-family",
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"모델-a={candidate_path}",
            "--candidate",
            f"model-b={second_candidate_path}",
            "--qrels",
            str(qrels_path),
            "--cutoff",
            "1",
            "--include-artifact-digests",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["schema_version"] == FAMILY_OUTPUT_SCHEMA_VERSION_V2
    assert payload["artifacts"] == {
        "baseline_run": _digest(BASELINE_BYTES),
        "qrels": _digest(QRELS_BYTES),
        "candidates": [
            {"candidate_id": "모델-a", **_digest(CANDIDATE_BYTES)},
            {"candidate_id": "model-b", **_digest(SECOND_CANDIDATE_BYTES)},
        ],
    }
    assert [
        evidence["candidate_id"]
        for evidence in payload["artifacts"]["candidates"]
    ] == ["모델-a", "model-b"]
    assert str(tmp_path) not in captured.out


def test_default_schemas_remain_v1_without_artifact_evidence(tmp_path, capsys):
    baseline_path, candidate_path, second_candidate_path, qrels_path = (
        _write_artifacts(tmp_path)
    )

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
            ]
        )
        == 0
    )
    pairwise = json.loads(capsys.readouterr().out)
    assert pairwise["schema_version"] == OUTPUT_SCHEMA_VERSION
    assert "artifacts" not in pairwise

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
            ]
        )
        == 0
    )
    family = json.loads(capsys.readouterr().out)
    assert family["schema_version"] == FAMILY_OUTPUT_SCHEMA_VERSION
    assert "artifacts" not in family


def test_digest_changes_when_only_ignored_raw_comment_changes(tmp_path, capsys):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)
    first_arguments = [
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

    assert main(first_arguments) == 0
    first = json.loads(capsys.readouterr().out)
    candidate_path.write_bytes(b"# changed audit comment\n" + CANDIDATE_BYTES)
    assert main(first_arguments) == 0
    second = json.loads(capsys.readouterr().out)

    assert first["mean_difference"] == second["mean_difference"]
    assert (
        first["artifacts"]["candidate_run"]["sha256"]
        != second["artifacts"]["candidate_run"]["sha256"]
    )
    assert second["artifacts"]["candidate_run"]["byte_count"] == len(
        b"# changed audit comment\n" + CANDIDATE_BYTES
    )


def test_module_entrypoint_emits_utf8_v2_evidence_under_ascii_locale(tmp_path):
    baseline_path, candidate_path, _, qrels_path = _write_artifacts(tmp_path)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii:strict"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rankweave",
            "compare-family",
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"모델={candidate_path}",
            "--qrels",
            str(qrels_path),
            "--cutoff",
            "1",
            "--include-artifact-digests",
        ],
        check=False,
        capture_output=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    payload = json.loads(completed.stdout.decode("utf-8"))
    assert payload["schema_version"] == FAMILY_OUTPUT_SCHEMA_VERSION_V2
    assert payload["artifacts"]["candidates"][0]["candidate_id"] == "모델"


@pytest.mark.parametrize(
    ("projector", "message"),
    [
        (_artifact_digest_to_dict, "bounded text artifact"),
        (_pairwise_artifacts_to_dict, "pairwise artifact evidence"),
    ],
)
def test_digest_projectors_reject_wrong_evidence_types(projector, message):
    with pytest.raises(ValueError, match=message):
        projector(SimpleNamespace())


def test_family_digest_projector_rejects_wrong_evidence_type():
    report = compare_trec_run_family(
        BASELINE_BYTES.decode(),
        {"candidate": CANDIDATE_BYTES.decode()},
        QRELS_BYTES.decode(),
        cutoff=1,
    )

    with pytest.raises(ValueError, match="family artifact evidence"):
        _family_artifacts_to_dict(report, SimpleNamespace())


def test_family_digest_projector_requires_report_candidate_order():
    report = compare_trec_run_family(
        BASELINE_BYTES.decode(),
        {"candidate": CANDIDATE_BYTES.decode()},
        QRELS_BYTES.decode(),
        cutoff=1,
    )
    artifact = _empty_artifact()
    evidence = _FamilyArtifactEvidence(
        baseline_run=artifact,
        qrels=artifact,
        candidates=(
            _NamedArtifactEvidence(candidate_id="wrong", artifact=artifact),
        ),
    )

    with pytest.raises(ValueError, match="must match report order"):
        _family_artifacts_to_dict(report, evidence)
