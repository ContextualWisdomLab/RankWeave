import hashlib
from types import MappingProxyType

import pytest

from rankweave.artifact_verification import (
    FAMILY_REPORT_SCHEMA_VERSION,
    PAIRWISE_REPORT_SCHEMA_VERSION,
    ArtifactVerificationRecord,
    ArtifactVerificationReport,
    verify_report_artifacts,
)

BASELINE_BYTES = b"q Q0 other 1 0.9 baseline\n"
CANDIDATE_BYTES = b"q Q0 relevant 1 0.9 candidate\n"
SECOND_CANDIDATE_BYTES = b"q Q0 relevant 1 0.95 candidate-b\n"
QRELS_BYTES = b"q 0 relevant 1\n"


def _evidence(payload):
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
    }


def _pairwise_report():
    return {
        "schema_version": PAIRWISE_REPORT_SCHEMA_VERSION,
        "artifacts": {
            "baseline_run": _evidence(BASELINE_BYTES),
            "candidate_run": _evidence(CANDIDATE_BYTES),
            "qrels": _evidence(QRELS_BYTES),
        },
    }


def _family_report():
    return {
        "schema_version": FAMILY_REPORT_SCHEMA_VERSION,
        "candidate_count": 2,
        "candidates": [
            {"candidate_id": "first"},
            {"candidate_id": "second"},
        ],
        "artifacts": {
            "baseline_run": _evidence(BASELINE_BYTES),
            "qrels": _evidence(QRELS_BYTES),
            "candidates": [
                {"candidate_id": "first", **_evidence(CANDIDATE_BYTES)},
                {
                    "candidate_id": "second",
                    **_evidence(SECOND_CANDIDATE_BYTES),
                },
            ],
        },
    }


def _record(
    *,
    artifact_role="baseline_run",
    candidate_id=None,
    expected_sha256=None,
    actual_sha256=None,
    expected_byte_count=1,
    actual_byte_count=1,
):
    expected = expected_sha256 or hashlib.sha256(b"a").hexdigest()
    actual = actual_sha256 or expected
    return ArtifactVerificationRecord(
        artifact_role=artifact_role,
        candidate_id=candidate_id,
        expected_sha256=expected,
        actual_sha256=actual,
        expected_byte_count=expected_byte_count,
        actual_byte_count=actual_byte_count,
        sha256_matches=expected == actual,
        byte_count_matches=expected_byte_count == actual_byte_count,
    )


def test_pairwise_verification_returns_ordered_immutable_matching_evidence():
    result = verify_report_artifacts(
        MappingProxyType(_pairwise_report()),
        baseline_run_bytes=BASELINE_BYTES,
        candidate_run_bytes=CANDIDATE_BYTES,
        qrels_bytes=QRELS_BYTES,
    )

    assert result.report_schema_version == PAIRWISE_REPORT_SCHEMA_VERSION
    assert result.verified is True
    assert result.mismatch_count == 0
    assert [artifact.artifact_role for artifact in result.artifacts] == [
        "baseline_run",
        "candidate_run",
        "qrels",
    ]
    assert all(artifact.candidate_id is None for artifact in result.artifacts)
    assert all(artifact.verified for artifact in result.artifacts)
    with pytest.raises(AttributeError):
        result.report_schema_version = "changed"


def test_pairwise_mismatch_preserves_digest_and_byte_count_diagnostics():
    changed_candidate = CANDIDATE_BYTES + b"# changed\n"

    result = verify_report_artifacts(
        _pairwise_report(),
        baseline_run_bytes=BASELINE_BYTES,
        candidate_run_bytes=changed_candidate,
        qrels_bytes=QRELS_BYTES,
    )

    candidate = result.artifacts[1]
    assert result.verified is False
    assert result.mismatch_count == 1
    assert candidate.expected_sha256 == hashlib.sha256(CANDIDATE_BYTES).hexdigest()
    assert candidate.actual_sha256 == hashlib.sha256(changed_candidate).hexdigest()
    assert candidate.sha256_matches is False
    assert candidate.expected_byte_count == len(CANDIDATE_BYTES)
    assert candidate.actual_byte_count == len(changed_candidate)
    assert candidate.byte_count_matches is False
    assert candidate.verified is False


def test_digest_and_byte_count_are_compared_independently():
    report = _pairwise_report()
    report["artifacts"]["candidate_run"]["byte_count"] += 1

    result = verify_report_artifacts(
        report,
        baseline_run_bytes=BASELINE_BYTES,
        candidate_run_bytes=CANDIDATE_BYTES,
        qrels_bytes=QRELS_BYTES,
    )

    candidate = result.artifacts[1]
    assert candidate.sha256_matches is True
    assert candidate.byte_count_matches is False
    assert candidate.verified is False


def test_family_verification_preserves_report_and_mapping_order():
    result = verify_report_artifacts(
        _family_report(),
        baseline_run_bytes=BASELINE_BYTES,
        qrels_bytes=QRELS_BYTES,
        candidate_run_bytes_by_id={
            "first": CANDIDATE_BYTES,
            "second": SECOND_CANDIDATE_BYTES,
        },
    )

    assert result.report_schema_version == FAMILY_REPORT_SCHEMA_VERSION
    assert result.verified is True
    assert result.mismatch_count == 0
    assert [
        (artifact.artifact_role, artifact.candidate_id)
        for artifact in result.artifacts
    ] == [
        ("baseline_run", None),
        ("qrels", None),
        ("candidate_run", "first"),
        ("candidate_run", "second"),
    ]


def test_family_candidate_mismatch_is_localized_without_losing_order():
    result = verify_report_artifacts(
        _family_report(),
        baseline_run_bytes=BASELINE_BYTES,
        qrels_bytes=QRELS_BYTES,
        candidate_run_bytes_by_id={
            "first": CANDIDATE_BYTES,
            "second": b"different",
        },
    )

    assert result.verified is False
    assert result.mismatch_count == 1
    assert [artifact.verified for artifact in result.artifacts] == [
        True,
        True,
        True,
        False,
    ]


@pytest.mark.parametrize(
    "schema_version",
    [
        "rankweave.trec-comparison.v1",
        "rankweave.trec-family-comparison.v1",
        "rankweave.unknown.v9",
        None,
    ],
)
def test_reports_without_supported_v2_artifact_evidence_fail_closed(schema_version):
    report = _pairwise_report()
    report["schema_version"] = schema_version

    with pytest.raises(ValueError, match="supported v2 report schema"):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            candidate_run_bytes=CANDIDATE_BYTES,
            qrels_bytes=QRELS_BYTES,
        )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda report: report["artifacts"].update(extra={}),
            "artifacts must contain exactly",
        ),
        (
            lambda report: report["artifacts"]["baseline_run"].update(
                extra="forbidden"
            ),
            "baseline_run evidence must contain exactly",
        ),
        (
            lambda report: report["artifacts"]["baseline_run"].update(
                sha256="A" * 64
            ),
            "baseline_run sha256",
        ),
        (
            lambda report: report["artifacts"]["baseline_run"].update(
                sha256="not-a-digest"
            ),
            "baseline_run sha256",
        ),
        (
            lambda report: report["artifacts"]["baseline_run"].update(
                byte_count=-1
            ),
            "baseline_run byte_count",
        ),
        (
            lambda report: report["artifacts"]["baseline_run"].update(
                byte_count=True
            ),
            "baseline_run byte_count",
        ),
        (
            lambda report: report.update(artifacts=[]),
            "artifacts must be a mapping",
        ),
    ],
)
def test_pairwise_artifact_evidence_is_strict(mutator, message):
    report = _pairwise_report()
    mutator(report)

    with pytest.raises(ValueError, match=message):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            candidate_run_bytes=CANDIDATE_BYTES,
            qrels_bytes=QRELS_BYTES,
        )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda report: report.update(candidate_count=1),
            "candidate_count must equal",
        ),
        (
            lambda report: report["candidates"].reverse(),
            "candidate identifiers must match",
        ),
        (
            lambda report: report["artifacts"]["candidates"].reverse(),
            "candidate identifiers must match",
        ),
        (
            lambda report: report["artifacts"]["candidates"][1].update(
                candidate_id="first"
            ),
            "candidate identifiers must be unique",
        ),
        (
            lambda report: report["artifacts"]["candidates"][0].update(
                candidate_id=" bad"
            ),
            "candidate identifier must not have",
        ),
        (
            lambda report: report["artifacts"]["candidates"][0].update(
                candidate_id="bad=id"
            ),
            "candidate identifier must not contain",
        ),
        (
            lambda report: report["artifacts"]["candidates"][0].update(
                candidate_id="bad\n"
            ),
            "candidate identifier must contain printable",
        ),
        (
            lambda report: report["artifacts"]["candidates"][0].update(
                extra="forbidden"
            ),
            "candidate evidence must contain exactly",
        ),
        (
            lambda report: report.update(candidates="wrong"),
            "report candidates must be a sequence",
        ),
        (
            lambda report: report["artifacts"].update(candidates="wrong"),
            "artifact candidates must be a sequence",
        ),
    ],
)
def test_family_report_and_evidence_alignment_fail_closed(mutator, message):
    report = _family_report()
    mutator(report)

    with pytest.raises(ValueError, match=message):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={
                "first": CANDIDATE_BYTES,
                "second": SECOND_CANDIDATE_BYTES,
            },
        )


def test_family_supplied_candidates_must_match_exact_report_order():
    with pytest.raises(ValueError, match="supplied candidate identifiers must match"):
        verify_report_artifacts(
            _family_report(),
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={
                "second": SECOND_CANDIDATE_BYTES,
                "first": CANDIDATE_BYTES,
            },
        )


@pytest.mark.parametrize(
    ("report_factory", "candidate_bytes", "candidate_mapping", "message"),
    [
        (_pairwise_report, None, None, "candidate_run_bytes is required"),
        (
            _pairwise_report,
            CANDIDATE_BYTES,
            {"first": CANDIDATE_BYTES},
            "candidate_run_bytes_by_id must be omitted",
        ),
        (
            _family_report,
            CANDIDATE_BYTES,
            {
                "first": CANDIDATE_BYTES,
                "second": SECOND_CANDIDATE_BYTES,
            },
            "candidate_run_bytes must be omitted",
        ),
        (_family_report, None, None, "candidate_run_bytes_by_id is required"),
        (_family_report, None, {}, "candidate_run_bytes_by_id must not be empty"),
    ],
)
def test_pairwise_and_family_input_modes_are_mutually_exclusive(
    report_factory, candidate_bytes, candidate_mapping, message
):
    with pytest.raises(ValueError, match=message):
        verify_report_artifacts(
            report_factory(),
            baseline_run_bytes=BASELINE_BYTES,
            candidate_run_bytes=candidate_bytes,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id=candidate_mapping,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("report", [], "report must be a mapping"),
        ("baseline_run_bytes", bytearray(BASELINE_BYTES), "must be bytes"),
        ("qrels_bytes", "text", "must be bytes"),
        ("candidate_run_bytes", memoryview(CANDIDATE_BYTES), "must be bytes"),
    ],
)
def test_public_inputs_reject_mutable_or_wrong_types(field, value, message):
    arguments = {
        "report": _pairwise_report(),
        "baseline_run_bytes": BASELINE_BYTES,
        "candidate_run_bytes": CANDIDATE_BYTES,
        "qrels_bytes": QRELS_BYTES,
    }
    arguments[field] = value

    with pytest.raises(ValueError, match=message):
        verify_report_artifacts(**arguments)


def test_family_candidate_values_must_be_immutable_bytes():
    with pytest.raises(ValueError, match="candidate 'second' bytes must be bytes"):
        verify_report_artifacts(
            _family_report(),
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={
                "first": CANDIDATE_BYTES,
                "second": bytearray(SECOND_CANDIDATE_BYTES),
            },
        )


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            lambda: _record(artifact_role="unknown"),
            "artifact_role must be one of",
        ),
        (
            lambda: _record(artifact_role="baseline_run", candidate_id="first"),
            "candidate_id is only allowed",
        ),
        (
            lambda: _record(artifact_role="candidate_run", candidate_id=" bad"),
            "candidate identifier must not have",
        ),
        (
            lambda: ArtifactVerificationRecord(
                artifact_role="baseline_run",
                candidate_id=None,
                expected_sha256=hashlib.sha256(b"a").hexdigest(),
                actual_sha256=hashlib.sha256(b"a").hexdigest(),
                expected_byte_count=1,
                actual_byte_count=1,
                sha256_matches=False,
                byte_count_matches=True,
            ),
            "sha256_matches must equal",
        ),
        (
            lambda: ArtifactVerificationRecord(
                artifact_role="baseline_run",
                candidate_id=None,
                expected_sha256=hashlib.sha256(b"a").hexdigest(),
                actual_sha256=hashlib.sha256(b"a").hexdigest(),
                expected_byte_count=1,
                actual_byte_count=1,
                sha256_matches=True,
                byte_count_matches=False,
            ),
            "byte_count_matches must equal",
        ),
    ],
)
def test_public_verification_record_rejects_inconsistent_state(record, message):
    with pytest.raises(ValueError, match=message):
        record()


def test_public_verification_report_rejects_wrong_schema_and_artifact_order():
    baseline = _record()
    candidate = _record(artifact_role="candidate_run")
    qrels = _record(artifact_role="qrels")

    with pytest.raises(ValueError, match="report_schema_version must be one of"):
        ArtifactVerificationReport("unknown", (baseline, candidate, qrels))
    with pytest.raises(ValueError, match="pairwise artifact order"):
        ArtifactVerificationReport(
            PAIRWISE_REPORT_SCHEMA_VERSION,
            (baseline, qrels, candidate),
        )
    with pytest.raises(ValueError, match="family artifact order"):
        ArtifactVerificationReport(
            FAMILY_REPORT_SCHEMA_VERSION,
            (baseline, candidate, qrels),
        )
    with pytest.raises(ValueError, match="artifacts must be a non-empty tuple"):
        ArtifactVerificationReport(PAIRWISE_REPORT_SCHEMA_VERSION, ())
