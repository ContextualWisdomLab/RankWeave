"""Verify local artifact bytes against evidence in RankWeave v2 reports."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

PAIRWISE_REPORT_SCHEMA_VERSION = "rankweave.trec-comparison.v2"
FAMILY_REPORT_SCHEMA_VERSION = "rankweave.trec-family-comparison.v2"
SUPPORTED_REPORT_SCHEMA_VERSIONS = (
    PAIRWISE_REPORT_SCHEMA_VERSION,
    FAMILY_REPORT_SCHEMA_VERSION,
)
SUPPORTED_ARTIFACT_ROLES = (
    "baseline_run",
    "candidate_run",
    "qrels",
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _require_nonnegative_integer(value: object, label: str) -> int:
    """Return a non-negative integer, rejecting booleans and wrong types."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _require_sha256(value: object, label: str) -> str:
    """Return one canonical lowercase SHA-256 hexadecimal digest."""
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(
            f"{label} must be 64 lowercase hexadecimal characters"
        )
    return value


def _require_candidate_id(value: object) -> str:
    """Return one printable, portable candidate identifier."""
    if not isinstance(value, str) or not value:
        raise ValueError("candidate identifier must be a non-empty string")
    if not all(character.isprintable() for character in value):
        raise ValueError(
            "candidate identifier must contain printable characters"
        )
    if value != value.strip():
        raise ValueError(
            "candidate identifier must not have leading or trailing "
            "whitespace"
        )
    if "=" in value:
        raise ValueError("candidate identifier must not contain '='")
    return value


def _require_bytes(value: object, label: str) -> bytes:
    """Return immutable raw bytes for one artifact role."""
    if not isinstance(value, bytes):
        raise ValueError(f"{label} must be bytes")
    return value


def _require_mapping(
    value: object,
    label: str,
) -> Mapping[str, object]:
    """Return a mapping or raise one stable validation error."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _require_sequence(value: object, label: str) -> Sequence[object]:
    """Return a non-string sequence or raise one stable error."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value,
        Sequence,
    ):
        raise ValueError(f"{label} must be a sequence")
    return value


def _require_exact_keys(
    value: Mapping[str, object],
    expected_keys: tuple[str, ...],
    label: str,
) -> None:
    """Require a mapping to expose exactly the declared keys."""
    if set(value) != set(expected_keys):
        raise ValueError(
            f"{label} must contain exactly {expected_keys!r}"
        )


def _require_unique_candidate_ids(
    candidate_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Return candidate identifiers after enforcing uniqueness."""
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate identifiers must be unique")
    return candidate_ids


def _parse_artifact_evidence(
    value: object,
    *,
    label: str,
) -> tuple[str, int]:
    """Parse one strict path-free artifact evidence mapping."""
    evidence = _require_mapping(value, f"{label} evidence")
    _require_exact_keys(
        evidence,
        ("sha256", "byte_count"),
        f"{label} evidence",
    )
    return (
        _require_sha256(evidence["sha256"], f"{label} sha256"),
        _require_nonnegative_integer(
            evidence["byte_count"],
            f"{label} byte_count",
        ),
    )


def _parse_named_candidate_evidence(
    value: object,
) -> tuple[str, str, int]:
    """Parse one strict candidate and artifact evidence mapping."""
    evidence = _require_mapping(value, "candidate evidence")
    _require_exact_keys(
        evidence,
        ("candidate_id", "sha256", "byte_count"),
        "candidate evidence",
    )
    candidate_id = _require_candidate_id(evidence["candidate_id"])
    return (
        candidate_id,
        _require_sha256(
            evidence["sha256"],
            f"candidate {candidate_id!r} sha256",
        ),
        _require_nonnegative_integer(
            evidence["byte_count"],
            f"candidate {candidate_id!r} byte_count",
        ),
    )


def _report_candidate_ids(value: object) -> tuple[str, ...]:
    """Extract ordered identifiers from report result records."""
    candidates = _require_sequence(value, "report candidates")
    identifiers: list[str] = []
    for candidate in candidates:
        candidate_mapping = _require_mapping(
            candidate,
            "report candidate",
        )
        if "candidate_id" not in candidate_mapping:
            raise ValueError(
                "report candidate must contain candidate_id"
            )
        identifiers.append(
            _require_candidate_id(candidate_mapping["candidate_id"])
        )
    return _require_unique_candidate_ids(tuple(identifiers))


@dataclass(frozen=True)
class ArtifactVerificationRecord:
    """Describe expected and observed evidence for one artifact."""

    artifact_role: str
    candidate_id: str | None
    expected_sha256: str
    actual_sha256: str
    expected_byte_count: int
    actual_byte_count: int
    sha256_matches: bool
    byte_count_matches: bool

    def __post_init__(self) -> None:
        """Reject inconsistent public verification state."""
        if self.artifact_role not in SUPPORTED_ARTIFACT_ROLES:
            raise ValueError(
                "artifact_role must be one of "
                f"{SUPPORTED_ARTIFACT_ROLES!r}"
            )
        if self.candidate_id is not None:
            _require_candidate_id(self.candidate_id)
            if self.artifact_role != "candidate_run":
                raise ValueError(
                    "candidate_id is only allowed for candidate_run "
                    "records"
                )
        _require_sha256(self.expected_sha256, "expected_sha256")
        _require_sha256(self.actual_sha256, "actual_sha256")
        _require_nonnegative_integer(
            self.expected_byte_count,
            "expected_byte_count",
        )
        _require_nonnegative_integer(
            self.actual_byte_count,
            "actual_byte_count",
        )
        if not isinstance(self.sha256_matches, bool):
            raise ValueError("sha256_matches must be boolean")
        if not isinstance(self.byte_count_matches, bool):
            raise ValueError("byte_count_matches must be boolean")
        if self.sha256_matches != (
            self.expected_sha256 == self.actual_sha256
        ):
            raise ValueError(
                "sha256_matches must equal the digest comparison "
                "result"
            )
        if self.byte_count_matches != (
            self.expected_byte_count == self.actual_byte_count
        ):
            raise ValueError(
                "byte_count_matches must equal the byte-count "
                "comparison result"
            )

    @property
    def verified(self) -> bool:
        """Return whether digest and byte count both match."""
        return self.sha256_matches and self.byte_count_matches


@dataclass(frozen=True)
class ArtifactVerificationReport:
    """Collect ordered verification evidence for one v2 report."""

    report_schema_version: str
    artifacts: tuple[ArtifactVerificationRecord, ...]

    def __post_init__(self) -> None:
        """Require one valid pairwise or family artifact ordering."""
        if (
            self.report_schema_version
            not in SUPPORTED_REPORT_SCHEMA_VERSIONS
        ):
            raise ValueError(
                "report_schema_version must be one of "
                f"{SUPPORTED_REPORT_SCHEMA_VERSIONS!r}"
            )
        if not isinstance(self.artifacts, tuple) or not self.artifacts:
            raise ValueError("artifacts must be a non-empty tuple")
        if not all(
            isinstance(artifact, ArtifactVerificationRecord)
            for artifact in self.artifacts
        ):
            raise ValueError(
                "artifacts must contain ArtifactVerificationRecord "
                "values"
            )

        if (
            self.report_schema_version
            == PAIRWISE_REPORT_SCHEMA_VERSION
        ):
            if tuple(
                (artifact.artifact_role, artifact.candidate_id)
                for artifact in self.artifacts
            ) != (
                ("baseline_run", None),
                ("candidate_run", None),
                ("qrels", None),
            ):
                raise ValueError(
                    "pairwise artifact order must be baseline_run, "
                    "candidate_run, qrels"
                )
            return

        if len(self.artifacts) < 3:
            raise ValueError(
                "family artifact order must be baseline_run, qrels, "
                "then named candidate_run records"
            )
        if (
            self.artifacts[0].artifact_role != "baseline_run"
            or self.artifacts[0].candidate_id is not None
            or self.artifacts[1].artifact_role != "qrels"
            or self.artifacts[1].candidate_id is not None
            or any(
                artifact.artifact_role != "candidate_run"
                or artifact.candidate_id is None
                for artifact in self.artifacts[2:]
            )
        ):
            raise ValueError(
                "family artifact order must be baseline_run, qrels, "
                "then named candidate_run records"
            )
        _require_unique_candidate_ids(
            tuple(
                artifact.candidate_id
                for artifact in self.artifacts[2:]
                if artifact.candidate_id is not None
            )
        )

    @property
    def verified(self) -> bool:
        """Return whether every artifact matches its evidence."""
        return all(
            artifact.verified for artifact in self.artifacts
        )

    @property
    def mismatch_count(self) -> int:
        """Return artifacts with any evidence mismatch."""
        return sum(
            not artifact.verified for artifact in self.artifacts
        )


def _verification_record(
    *,
    artifact_role: str,
    candidate_id: str | None,
    expected_sha256: str,
    expected_byte_count: int,
    actual_bytes: bytes,
) -> ArtifactVerificationRecord:
    """Build one expected-versus-observed verification record."""
    actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()
    actual_byte_count = len(actual_bytes)
    return ArtifactVerificationRecord(
        artifact_role=artifact_role,
        candidate_id=candidate_id,
        expected_sha256=expected_sha256,
        actual_sha256=actual_sha256,
        expected_byte_count=expected_byte_count,
        actual_byte_count=actual_byte_count,
        sha256_matches=expected_sha256 == actual_sha256,
        byte_count_matches=(
            expected_byte_count == actual_byte_count
        ),
    )


def _verify_pairwise_report(
    report: Mapping[str, object],
    *,
    baseline_run_bytes: bytes,
    qrels_bytes: bytes,
    candidate_run_bytes: bytes | None,
    candidate_run_bytes_by_id: Mapping[str, bytes] | None,
) -> ArtifactVerificationReport:
    """Verify one pairwise v2 report against three artifacts."""
    if candidate_run_bytes is None:
        raise ValueError(
            "candidate_run_bytes is required for pairwise report"
        )
    validated_candidate_bytes = _require_bytes(
        candidate_run_bytes,
        "candidate_run_bytes",
    )
    if candidate_run_bytes_by_id is not None:
        raise ValueError(
            "candidate_run_bytes_by_id must be omitted for pairwise "
            "report"
        )
    artifacts = _require_mapping(
        report.get("artifacts"),
        "artifacts",
    )
    _require_exact_keys(
        artifacts,
        ("baseline_run", "candidate_run", "qrels"),
        "artifacts",
    )
    baseline_digest, baseline_count = _parse_artifact_evidence(
        artifacts["baseline_run"],
        label="baseline_run",
    )
    candidate_digest, candidate_count = _parse_artifact_evidence(
        artifacts["candidate_run"],
        label="candidate_run",
    )
    qrels_digest, qrels_count = _parse_artifact_evidence(
        artifacts["qrels"],
        label="qrels",
    )
    return ArtifactVerificationReport(
        report_schema_version=PAIRWISE_REPORT_SCHEMA_VERSION,
        artifacts=(
            _verification_record(
                artifact_role="baseline_run",
                candidate_id=None,
                expected_sha256=baseline_digest,
                expected_byte_count=baseline_count,
                actual_bytes=baseline_run_bytes,
            ),
            _verification_record(
                artifact_role="candidate_run",
                candidate_id=None,
                expected_sha256=candidate_digest,
                expected_byte_count=candidate_count,
                actual_bytes=validated_candidate_bytes,
            ),
            _verification_record(
                artifact_role="qrels",
                candidate_id=None,
                expected_sha256=qrels_digest,
                expected_byte_count=qrels_count,
                actual_bytes=qrels_bytes,
            ),
        ),
    )


def _verify_family_report(
    report: Mapping[str, object],
    *,
    baseline_run_bytes: bytes,
    qrels_bytes: bytes,
    candidate_run_bytes: bytes | None,
    candidate_run_bytes_by_id: Mapping[str, bytes] | None,
) -> ArtifactVerificationReport:
    """Verify one family v2 report with exact ID alignment."""
    if candidate_run_bytes is not None:
        raise ValueError(
            "candidate_run_bytes must be omitted for family report"
        )
    if candidate_run_bytes_by_id is None:
        raise ValueError(
            "candidate_run_bytes_by_id is required for family report"
        )
    if not isinstance(candidate_run_bytes_by_id, Mapping):
        raise ValueError(
            "candidate_run_bytes_by_id must be a mapping"
        )
    if not candidate_run_bytes_by_id:
        raise ValueError(
            "candidate_run_bytes_by_id must not be empty"
        )

    supplied_candidates: list[tuple[str, bytes]] = []
    for candidate_id, candidate_bytes in (
        candidate_run_bytes_by_id.items()
    ):
        validated_candidate_id = _require_candidate_id(candidate_id)
        supplied_candidates.append(
            (
                validated_candidate_id,
                _require_bytes(
                    candidate_bytes,
                    f"candidate {validated_candidate_id!r} bytes",
                ),
            )
        )
    supplied_ids = _require_unique_candidate_ids(
        tuple(
            candidate_id
            for candidate_id, _ in supplied_candidates
        )
    )

    artifacts = _require_mapping(
        report.get("artifacts"),
        "artifacts",
    )
    _require_exact_keys(
        artifacts,
        ("baseline_run", "qrels", "candidates"),
        "artifacts",
    )
    baseline_digest, baseline_count = _parse_artifact_evidence(
        artifacts["baseline_run"],
        label="baseline_run",
    )
    qrels_digest, qrels_count = _parse_artifact_evidence(
        artifacts["qrels"],
        label="qrels",
    )

    evidence_sequence = _require_sequence(
        artifacts["candidates"],
        "artifact candidates",
    )
    parsed_evidence = tuple(
        _parse_named_candidate_evidence(value)
        for value in evidence_sequence
    )
    evidence_ids = _require_unique_candidate_ids(
        tuple(
            candidate_id
            for candidate_id, _, _ in parsed_evidence
        )
    )
    report_ids = _report_candidate_ids(
        report.get("candidates")
    )
    candidate_count = _require_nonnegative_integer(
        report.get("candidate_count"),
        "candidate_count",
    )
    if (
        candidate_count != len(report_ids)
        or candidate_count != len(evidence_ids)
    ):
        raise ValueError(
            "candidate_count must equal report and artifact "
            "candidate counts"
        )
    if report_ids != evidence_ids:
        raise ValueError(
            "report and artifact candidate identifiers must match "
            "in order"
        )
    if supplied_ids != report_ids:
        raise ValueError(
            "supplied candidate identifiers must match report order"
        )

    candidate_bytes_by_id = dict(supplied_candidates)
    candidate_records = tuple(
        _verification_record(
            artifact_role="candidate_run",
            candidate_id=candidate_id,
            expected_sha256=expected_sha256,
            expected_byte_count=expected_byte_count,
            actual_bytes=candidate_bytes_by_id[candidate_id],
        )
        for (
            candidate_id,
            expected_sha256,
            expected_byte_count,
        ) in parsed_evidence
    )
    return ArtifactVerificationReport(
        report_schema_version=FAMILY_REPORT_SCHEMA_VERSION,
        artifacts=(
            _verification_record(
                artifact_role="baseline_run",
                candidate_id=None,
                expected_sha256=baseline_digest,
                expected_byte_count=baseline_count,
                actual_bytes=baseline_run_bytes,
            ),
            _verification_record(
                artifact_role="qrels",
                candidate_id=None,
                expected_sha256=qrels_digest,
                expected_byte_count=qrels_count,
                actual_bytes=qrels_bytes,
            ),
            *candidate_records,
        ),
    )


def verify_report_artifacts(
    report: Mapping[str, object],
    *,
    baseline_run_bytes: bytes,
    qrels_bytes: bytes,
    candidate_run_bytes: bytes | None = None,
    candidate_run_bytes_by_id: Mapping[str, bytes] | None = None,
) -> ArtifactVerificationReport:
    """Verify explicit local bytes against one RankWeave v2 report.

    This compares exact raw bytes with unsigned SHA-256 and byte-count
    evidence. It does not authenticate a producer, verify a signature
    or provenance envelope, or establish any SLSA level.
    """
    validated_report = _require_mapping(report, "report")
    validated_baseline = _require_bytes(
        baseline_run_bytes,
        "baseline_run_bytes",
    )
    validated_qrels = _require_bytes(
        qrels_bytes,
        "qrels_bytes",
    )
    schema_version = validated_report.get("schema_version")
    if schema_version not in SUPPORTED_REPORT_SCHEMA_VERSIONS:
        raise ValueError(
            "report must use a supported v2 report schema: "
            f"{SUPPORTED_REPORT_SCHEMA_VERSIONS!r}"
        )
    if schema_version == PAIRWISE_REPORT_SCHEMA_VERSION:
        return _verify_pairwise_report(
            validated_report,
            baseline_run_bytes=validated_baseline,
            qrels_bytes=validated_qrels,
            candidate_run_bytes=candidate_run_bytes,
            candidate_run_bytes_by_id=(
                candidate_run_bytes_by_id
            ),
        )
    return _verify_family_report(
        validated_report,
        baseline_run_bytes=validated_baseline,
        qrels_bytes=validated_qrels,
        candidate_run_bytes=candidate_run_bytes,
        candidate_run_bytes_by_id=candidate_run_bytes_by_id,
    )
