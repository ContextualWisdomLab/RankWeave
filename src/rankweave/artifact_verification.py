"""Verify local artifact bytes against evidence in RankWeave v2 reports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

PAIRWISE_REPORT_SCHEMA_VERSION = "rankweave.trec-comparison.v2"
FAMILY_REPORT_SCHEMA_VERSION = "rankweave.trec-family-comparison.v2"


@dataclass(frozen=True)
class ArtifactVerificationRecord:
    """Describe expected and observed evidence for one supplied artifact."""

    artifact_role: str
    candidate_id: str | None
    expected_sha256: str
    actual_sha256: str
    expected_byte_count: int
    actual_byte_count: int
    sha256_matches: bool
    byte_count_matches: bool

    @property
    def verified(self) -> bool:
        """Return whether both digest and byte count match."""
        return self.sha256_matches and self.byte_count_matches


@dataclass(frozen=True)
class ArtifactVerificationReport:
    """Collect ordered artifact-verification evidence for one v2 report."""

    report_schema_version: str
    artifacts: tuple[ArtifactVerificationRecord, ...]

    @property
    def verified(self) -> bool:
        """Return whether every artifact matches its report evidence."""
        return all(artifact.verified for artifact in self.artifacts)

    @property
    def mismatch_count(self) -> int:
        """Return the number of artifacts with any evidence mismatch."""
        return sum(not artifact.verified for artifact in self.artifacts)


def verify_report_artifacts(
    report: Mapping[str, object],
    *,
    baseline_run_bytes: bytes,
    qrels_bytes: bytes,
    candidate_run_bytes: bytes | None = None,
    candidate_run_bytes_by_id: Mapping[str, bytes] | None = None,
) -> ArtifactVerificationReport:
    """Verify explicit local bytes against one RankWeave v2 report."""
    raise NotImplementedError("report artifact verification is not implemented")
