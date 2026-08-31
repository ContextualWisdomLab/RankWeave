"""Typed adapter for immutable exact semantic-unit index snapshots."""

from collections.abc import Sequence
from dataclasses import dataclass

from rankweave import _rankweave_core
from rankweave.semantic_vector_ranking import SemanticUnitRank


@dataclass(frozen=True)
class SemanticIndexSnapshotEvidence:
    """Integrity evidence for one immutable owner index snapshot."""

    schema_version: str
    snapshot_version: str
    model_digest: str
    dimension_digest: str
    vectors_digest: str
    snapshot_digest: str
    vector_dimension: int
    candidate_count: int


@dataclass(frozen=True)
class SemanticIndexRankingReport:
    """Exact authorization-scoped ranking from one immutable snapshot."""

    snapshot: SemanticIndexSnapshotEvidence
    algorithm_version: str
    execution_profile: str
    worker_count: int
    ordered_input_digest: str
    output_digest: str
    results: tuple[SemanticUnitRank, ...]


class SemanticUnitExactIndex:
    """Own one atomically replaceable exact Rust index snapshot."""

    def __init__(
        self,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
        candidate_ids: Sequence[tuple[str, str]],
        packed_vectors: bytes,
    ) -> None:
        """Build the initial immutable snapshot before exposing the index."""

        self._native = _rankweave_core.SemanticUnitIndex(
            snapshot_version,
            model_identity,
            vector_dimension,
            list(candidate_ids),
            packed_vectors,
        )

    @property
    def snapshot_evidence(self) -> SemanticIndexSnapshotEvidence:
        """Return integrity evidence for the currently active snapshot."""

        return SemanticIndexSnapshotEvidence(*self._native.snapshot_evidence())

    def replace_snapshot(
        self,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
        candidate_ids: Sequence[tuple[str, str]],
        packed_vectors: bytes,
    ) -> None:
        """Build fully, then atomically replace the active immutable snapshot."""

        self._native.replace_snapshot(
            snapshot_version,
            model_identity,
            vector_dimension,
            list(candidate_ids),
            packed_vectors,
        )

    def rank_authorized(
        self,
        model_identity: str,
        query_vector: Sequence[float],
        authorized_candidate_ids: Sequence[tuple[str, str]],
    ) -> SemanticIndexRankingReport:
        """Rank exactly and return no identity absent from caller authorization."""

        (
            snapshot,
            algorithm,
            execution_profile,
            worker_count,
            input_digest,
            output_digest,
            rows,
        ) = self._native.rank_authorized(
            model_identity,
            list(query_vector),
            list(authorized_candidate_ids),
        )
        return SemanticIndexRankingReport(
            snapshot=SemanticIndexSnapshotEvidence(*snapshot),
            algorithm_version=algorithm,
            execution_profile=execution_profile,
            worker_count=worker_count,
            ordered_input_digest=input_digest,
            output_digest=output_digest,
            results=tuple(SemanticUnitRank(*row) for row in rows),
        )

    def rank_authorized_packed(
        self,
        model_identity: str,
        query_vector: Sequence[float],
        packed_authorization: bytes,
    ) -> SemanticIndexRankingReport:
        """Rank a canonical length-prefixed authorization byte buffer."""
        (
            snapshot,
            algorithm,
            execution_profile,
            worker_count,
            input_digest,
            output_digest,
            rows,
        ) = self._native.rank_authorized_packed(
            model_identity,
            list(query_vector),
            packed_authorization,
        )
        return SemanticIndexRankingReport(
            snapshot=SemanticIndexSnapshotEvidence(*snapshot),
            algorithm_version=algorithm,
            execution_profile=execution_profile,
            worker_count=worker_count,
            ordered_input_digest=input_digest,
            output_digest=output_digest,
            results=tuple(SemanticUnitRank(*row) for row in rows),
        )
