import hashlib

import pytest

from rankweave.artifact_verification import (
    FAMILY_REPORT_SCHEMA_VERSION,
    PAIRWISE_REPORT_SCHEMA_VERSION,
    ArtifactVerificationRecord,
    ArtifactVerificationReport,
    verify_report_artifacts,
)

DIGEST = hashlib.sha256(b"a").hexdigest()
BASELINE_BYTES = b"baseline"
CANDIDATE_BYTES = b"candidate"
QRELS_BYTES = b"qrels"


def _evidence(payload):
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
    }


def _family_report():
    return {
        "schema_version": FAMILY_REPORT_SCHEMA_VERSION,
        "candidate_count": 1,
        "candidates": [{"candidate_id": "first"}],
        "artifacts": {
            "baseline_run": _evidence(BASELINE_BYTES),
            "qrels": _evidence(QRELS_BYTES),
            "candidates": [
                {"candidate_id": "first", **_evidence(CANDIDATE_BYTES)}
            ],
        },
    }


def _record(*, role="baseline_run", candidate_id=None):
    return ArtifactVerificationRecord(
        artifact_role=role,
        candidate_id=candidate_id,
        expected_sha256=DIGEST,
        actual_sha256=DIGEST,
        expected_byte_count=1,
        actual_byte_count=1,
        sha256_matches=True,
        byte_count_matches=True,
    )


@pytest.mark.parametrize("candidate_id", ["", 1])
def test_candidate_identifiers_must_be_nonempty_strings(candidate_id):
    report = _family_report()
    report["artifacts"]["candidates"][0]["candidate_id"] = candidate_id

    with pytest.raises(ValueError, match="non-empty string"):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={"first": CANDIDATE_BYTES},
        )


def test_report_candidate_records_require_candidate_identifier():
    report = _family_report()
    report["candidates"] = [{}]

    with pytest.raises(ValueError, match="must contain candidate_id"):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={"first": CANDIDATE_BYTES},
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sha256_matches", 1, "sha256_matches must be boolean"),
        ("byte_count_matches", 1, "byte_count_matches must be boolean"),
        ("expected_sha256", "bad", "expected_sha256"),
        ("actual_sha256", "bad", "actual_sha256"),
        ("expected_byte_count", True, "expected_byte_count"),
        ("actual_byte_count", -1, "actual_byte_count"),
    ],
)
def test_public_record_rejects_wrong_field_types(field, value, message):
    arguments = {
        "artifact_role": "baseline_run",
        "candidate_id": None,
        "expected_sha256": DIGEST,
        "actual_sha256": DIGEST,
        "expected_byte_count": 1,
        "actual_byte_count": 1,
        "sha256_matches": True,
        "byte_count_matches": True,
    }
    arguments[field] = value

    with pytest.raises(ValueError, match=message):
        ArtifactVerificationRecord(**arguments)


def test_public_report_requires_tuple_records():
    with pytest.raises(ValueError, match="non-empty tuple"):
        ArtifactVerificationReport(
            PAIRWISE_REPORT_SCHEMA_VERSION,
            [_record(), _record(role="candidate_run"), _record(role="qrels")],
        )
    with pytest.raises(ValueError, match="ArtifactVerificationRecord"):
        ArtifactVerificationReport(
            PAIRWISE_REPORT_SCHEMA_VERSION,
            (_record(), object(), _record(role="qrels")),
        )


def test_family_public_report_requires_at_least_one_named_candidate():
    with pytest.raises(ValueError, match="family artifact order"):
        ArtifactVerificationReport(
            FAMILY_REPORT_SCHEMA_VERSION,
            (_record(), _record(role="qrels")),
        )


def test_family_public_report_rejects_duplicate_candidate_identifiers():
    with pytest.raises(ValueError, match="candidate identifiers must be unique"):
        ArtifactVerificationReport(
            FAMILY_REPORT_SCHEMA_VERSION,
            (
                _record(),
                _record(role="qrels"),
                _record(role="candidate_run", candidate_id="first"),
                _record(role="candidate_run", candidate_id="first"),
            ),
        )


def test_family_candidate_mapping_must_be_a_mapping():
    with pytest.raises(ValueError, match="must be a mapping"):
        verify_report_artifacts(
            _family_report(),
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id=[("first", CANDIDATE_BYTES)],
        )


@pytest.mark.parametrize("candidate_count", [None, True, -1])
def test_family_candidate_count_must_be_nonnegative_integer(candidate_count):
    report = _family_report()
    report["candidate_count"] = candidate_count

    with pytest.raises(ValueError, match="candidate_count"):
        verify_report_artifacts(
            report,
            baseline_run_bytes=BASELINE_BYTES,
            qrels_bytes=QRELS_BYTES,
            candidate_run_bytes_by_id={"first": CANDIDATE_BYTES},
        )
