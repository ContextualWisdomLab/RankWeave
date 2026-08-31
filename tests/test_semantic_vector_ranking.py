import math
import struct

import pytest

from rankweave import (
    SemanticUnitCandidate,
    rank_semantic_units,
    rank_semantic_units_packed,
)


def test_semantic_units_return_versioned_winning_unit_evidence() -> None:
    report = rank_semantic_units(
        [1.0, 0.0],
        [
            SemanticUnitCandidate("item-b", "unit-z", [1.0, 0.0]),
            SemanticUnitCandidate("item-a", "unit-z", [1.0, 0.0]),
            SemanticUnitCandidate("item-c", "unit-b", [-1.0, 0.0]),
            SemanticUnitCandidate("item-c", "unit-a", [0.0, 1.0]),
        ],
    )

    assert report.schema_version == "rankweave.semantic-unit-ranking.v1"
    assert report.algorithm_version == "rankweave.semantic-unit-cosine.v1"
    assert report.ordered_input_digest.startswith("sha256:")
    assert report.vector_dimension == 2
    assert [
        (row.item_id, row.winning_unit_id, row.score) for row in report.results
    ] == [
        ("item-a", "unit-z", 1.0),
        ("item-b", "unit-z", 1.0),
        ("item-c", "unit-a", 0.0),
    ]


def test_packed_semantic_units_preserve_exact_report_and_digest() -> None:
    """Packed binary64 transport is identical to the scalar public contract."""

    query = [1.0, 0.0]
    candidate_ids = [("item-b", "unit-z"), ("item-a", "unit-z")]
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    scalar_report = rank_semantic_units(
        query,
        [
            SemanticUnitCandidate(item_id, unit_id, vector)
            for (item_id, unit_id), vector in zip(candidate_ids, vectors, strict=True)
        ],
    )

    packed_report = rank_semantic_units_packed(
        query,
        candidate_ids,
        b"".join(struct.pack(">2d", *vector) for vector in vectors),
    )

    assert packed_report == scalar_report


def test_packed_semantic_units_reject_wrong_byte_length() -> None:
    """Packed transport never pads or truncates a malformed vector payload."""

    with pytest.raises(ValueError, match="^packed_vector_byte_length:"):
        rank_semantic_units_packed([1.0, 0.0], [("item", "unit")], b"short")


@pytest.mark.parametrize(
    ("query", "candidates", "error_code"),
    [
        ([], [SemanticUnitCandidate("item", "unit", [1.0])], "empty_query_vector"),
        ([1.0], [], "empty_candidates"),
        (
            [math.inf],
            [SemanticUnitCandidate("item", "unit", [1.0])],
            "non_finite_vector",
        ),
        (
            [1.0],
            [SemanticUnitCandidate("item", "unit", [1.0, 2.0])],
            "dimension_mismatch",
        ),
        (
            [0.0],
            [SemanticUnitCandidate("item", "unit", [1.0])],
            "zero_norm_vector",
        ),
        (
            [1.0],
            [
                SemanticUnitCandidate("item", "unit", [1.0]),
                SemanticUnitCandidate("item", "unit", [1.0]),
            ],
            "duplicate_candidate",
        ),
    ],
)
def test_semantic_unit_failures_include_stable_codes(
    query: list[float],
    candidates: list[SemanticUnitCandidate],
    error_code: str,
) -> None:
    with pytest.raises(ValueError, match=f"^{error_code}:"):
        rank_semantic_units(query, candidates)
