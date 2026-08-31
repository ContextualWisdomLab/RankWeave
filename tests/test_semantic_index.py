import struct

import pytest

from rankweave import SemanticUnitExactIndex


def packed(*vectors: tuple[float, ...]) -> bytes:
    return b"".join(
        struct.pack(f">{len(vector)}d", *vector) for vector in vectors
    )


def packed_authorization(*identities: tuple[str, str]) -> bytes:
    payload = [len(identities).to_bytes(8, "big")]
    for identity in identities:
        for value in identity:
            encoded = value.encode("utf-8")
            payload.extend((len(encoded).to_bytes(8, "big"), encoded))
    return b"".join(payload)


def exact_index(version: str = "snapshot-v1") -> SemanticUnitExactIndex:
    return SemanticUnitExactIndex(
        version,
        "model-v1",
        2,
        [("item-b", "unit-z"), ("item-a", "unit-z"), ("item-a", "unit-a")],
        packed((1.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    )


def test_exact_index_returns_only_authorized_candidates() -> None:
    index = exact_index()

    report = index.rank_authorized(
        "model-v1",
        [1.0, 0.0],
        [("item-a", "unit-a")],
    )

    assert report.snapshot == index.snapshot_evidence
    assert report.snapshot.schema_version == "rankweave.semantic-unit-index-snapshot.v1"
    assert report.snapshot.vector_dimension == 2
    assert report.snapshot.candidate_count == 3
    assert report.execution_profile == "rankweave.semantic-unit-index.cpu-rayon.v1"
    assert report.ordered_input_digest.startswith("sha256:")
    assert report.output_digest.startswith("sha256:")
    actual = [
        (row.item_id, row.winning_unit_id, row.score) for row in report.results
    ]
    assert actual == [("item-a", "unit-a", 0.0)]


def test_exact_index_packed_authorization_matches_row_transport() -> None:
    index = exact_index()
    identities = (("item-a", "unit-a"),)

    rows = index.rank_authorized("model-v1", [1.0, 0.0], identities)
    packed_rows = index.rank_authorized_packed(
        "model-v1",
        [1.0, 0.0],
        packed_authorization(*identities),
    )

    assert packed_rows == rows


def test_exact_index_replacement_is_atomic_after_validation() -> None:
    index = exact_index()

    with pytest.raises(ValueError, match="^packed_vector_byte_length:"):
        index.replace_snapshot(
            "snapshot-v2",
            "model-v1",
            2,
            [("item", "unit")],
            b"short",
        )
    assert index.snapshot_evidence.snapshot_version == "snapshot-v1"

    replacement = exact_index("snapshot-v2")
    evidence = replacement.snapshot_evidence
    index.replace_snapshot(
        evidence.snapshot_version,
        "model-v1",
        2,
        [("item-b", "unit-z"), ("item-a", "unit-z"), ("item-a", "unit-a")],
        packed((1.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    )
    assert index.snapshot_evidence.snapshot_version == "snapshot-v2"


@pytest.mark.parametrize(
    ("model", "query", "authorization", "code"),
    [
        ("other-model", [1.0, 0.0], [("item-a", "unit-a")], "model_mismatch"),
        ("model-v1", [1.0], [("item-a", "unit-a")], "dimension_mismatch"),
        ("model-v1", [1.0, 0.0], [], "empty_authorization"),
        (
            "model-v1",
            [1.0, 0.0],
            [("missing", "unit")],
            "unknown_authorized_candidate",
        ),
    ],
)
def test_exact_index_fails_closed(
    model: str,
    query: list[float],
    authorization: list[tuple[str, str]],
    code: str,
) -> None:
    with pytest.raises(ValueError, match=f"^{code}:") as raised:
        exact_index().rank_authorized(model, query, authorization)
    assert str(raised.value).count(code) == 1
    assert "exact semantic index rejected input" in str(raised.value)
