import math

import pytest

from rankweave import SemanticUnitCandidate, rank_semantic_units


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
