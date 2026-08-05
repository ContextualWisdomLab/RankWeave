"""Machine-readable artifact-verification transport contracts."""

import copy
import hashlib

import pytest
from jsonschema import Draft202012Validator, ValidationError

from rankweave import load_report_schema, load_report_schema_text


def _record(role, payload, candidate_id=None):
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "artifact_role": role,
        "candidate_id": candidate_id,
        "expected_sha256": digest,
        "actual_sha256": digest,
        "sha256_matches": True,
        "expected_byte_count": len(payload),
        "actual_byte_count": len(payload),
        "byte_count_matches": True,
        "verified": True,
    }


def _verification_document():
    return {
        "schema_version": "rankweave.artifact-verification.v1",
        "rankweave_version": "0.17.0",
        "report_schema_version": "rankweave.trec-comparison.v2",
        "verified": True,
        "artifact_count": 3,
        "mismatch_count": 0,
        "artifacts": [
            _record("baseline_run", b"baseline"),
            _record("candidate_run", b"candidate"),
            _record("qrels", b"qrels"),
        ],
    }


def test_verification_schema_is_packaged_and_meta_schema_valid():
    """Expose canonical Draft 2020-12 verification schema text and data."""
    text = load_report_schema_text("verification", "v1")
    schema = load_report_schema("verification", "v1")

    assert text.endswith("\n")
    assert schema["properties"]["schema_version"]["const"] == (
        "rankweave.artifact-verification.v1"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_verification_document())


def test_verification_v2_selector_fails_as_unsupported_combination():
    """Distinguish a known type from a nonexistent transport version."""
    with pytest.raises(ValueError, match="schema combination is unsupported"):
        load_report_schema_text("verification", "v2")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.update(extra="forbidden"),
        lambda document: document["artifacts"][0].update(
            expected_sha256="not-a-digest"
        ),
        lambda document: document.update(mismatch_count=-1),
    ],
)
def test_verification_schema_rejects_representative_violations(mutation):
    """Reject extra fields, malformed digests, and negative counts."""
    document = copy.deepcopy(_verification_document())
    mutation(document)

    with pytest.raises(ValidationError):
        Draft202012Validator(
            load_report_schema("verification", "v1")
        ).validate(document)
