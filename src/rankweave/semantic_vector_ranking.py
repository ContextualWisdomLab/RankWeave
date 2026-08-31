"""Versioned semantic-unit cosine ranking backed by the Rust core."""

from collections.abc import Sequence
from dataclasses import dataclass

from rankweave import _rankweave_core


@dataclass(frozen=True)
class SemanticUnitCandidate:
    """One caller-authorized semantic unit and its provider-produced vector."""

    item_id: str
    unit_id: str
    vector: Sequence[float]


@dataclass(frozen=True)
class SemanticUnitRank:
    """The highest-scoring semantic unit retained for one item."""

    item_id: str
    winning_unit_id: str
    score: float


@dataclass(frozen=True)
class SemanticUnitRankingReport:
    """Versioned ranking and exact ordered-input integrity evidence."""

    schema_version: str
    algorithm_version: str
    ordered_input_digest: str
    vector_dimension: int
    results: tuple[SemanticUnitRank, ...]


def rank_semantic_units(
    query_vector: Sequence[float],
    candidates: Sequence[SemanticUnitCandidate],
) -> SemanticUnitRankingReport:
    """Rank items by their best semantic-unit cosine without selecting a model."""

    schema, algorithm, digest, dimension, rows = _rankweave_core.rank_semantic_units(
        list(query_vector),
        [
            (candidate.item_id, candidate.unit_id, list(candidate.vector))
            for candidate in candidates
        ],
    )
    return SemanticUnitRankingReport(
        schema_version=schema,
        algorithm_version=algorithm,
        ordered_input_digest=digest,
        vector_dimension=dimension,
        results=tuple(SemanticUnitRank(*row) for row in rows),
    )


def rank_semantic_units_packed(
    query_vector: Sequence[float],
    candidate_ids: Sequence[tuple[str, str]],
    packed_vectors: bytes,
) -> SemanticUnitRankingReport:
    """Rank canonical big-endian binary64 vectors without scalar expansion."""

    schema, algorithm, digest, dimension, rows = (
        _rankweave_core.rank_semantic_units_packed(
            list(query_vector),
            list(candidate_ids),
            packed_vectors,
        )
    )
    return SemanticUnitRankingReport(
        schema_version=schema,
        algorithm_version=algorithm,
        ordered_input_digest=digest,
        vector_dimension=dimension,
        results=tuple(SemanticUnitRank(*row) for row in rows),
    )
