import ast
import struct
from pathlib import Path

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


def test_exact_index_preflights_one_real_packed_authorization_scope() -> None:
    index = exact_index()
    authorization = packed_authorization(
        ("item-b", "unit-z"), ("item-a", "unit-z"), ("item-a", "unit-a")
    )

    report = index.preflight_authorized_packed("model-v1", authorization)
    top_k = index.preflight_authorized_top_k_packed("model-v1", authorization, 1)

    assert report.snapshot == index.snapshot_evidence
    assert {result.item_id for result in report.results} == {"item-a", "item-b"}
    assert report.ordered_input_digest.startswith("sha256:")
    assert report.output_digest.startswith("sha256:")
    assert top_k.results == report.results[:1]
    assert top_k.ordered_input_digest != report.ordered_input_digest


def test_exact_index_packed_batch_matches_independent_reports() -> None:
    index = exact_index()
    authorization = packed_authorization(
        ("item-b", "unit-z"), ("item-a", "unit-z"), ("item-a", "unit-a")
    )
    queries = ([1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0])

    batch = index.rank_authorized_batch_packed("model-v1", queries, authorization)
    independent = tuple(
        index.rank_authorized_packed("model-v1", query, authorization)
        for query in queries
    )

    assert batch == independent


def test_exact_index_packed_batch_rejects_empty_queries() -> None:
    with pytest.raises(ValueError, match="^empty_query_batch:"):
        exact_index().rank_authorized_batch_packed(
            "model-v1", [], packed_authorization(("item-a", "unit-a"))
        )


def test_exact_top_k_batch_matches_scalar_prefix_with_distinct_digest() -> None:
    index = exact_index()
    authorization = packed_authorization(
        ("item-b", "unit-z"), ("item-a", "unit-z"), ("item-a", "unit-a")
    )
    queries = ([1.0, 0.0], [0.0, 1.0])

    top_k = index.rank_authorized_top_k_batch_packed(
        "model-v1", queries, authorization, 1
    )
    full = index.rank_authorized_batch_packed("model-v1", queries, authorization)

    for top_k_report, full_report in zip(top_k, full, strict=True):
        assert top_k_report.results == full_report.results[:1]
        assert top_k_report.ordered_input_digest != full_report.ordered_input_digest
        assert top_k_report.output_digest != full_report.output_digest


def test_exact_top_k_batch_rejects_zero_k() -> None:
    with pytest.raises(ValueError, match="^empty_top_k:"):
        exact_index().rank_authorized_top_k_batch_packed(
            "model-v1",
            [[1.0, 0.0]],
            packed_authorization(("item-a", "unit-a")),
            0,
        )


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


def test_native_stub_declares_every_packed_scope_operation() -> None:
    stub = ast.parse(
        (Path(__file__).parents[1] / "src/rankweave/_rankweave_core.pyi").read_text(
            encoding="utf-8"
        )
    )
    index_class = next(
        node
        for node in stub.body
        if isinstance(node, ast.ClassDef) and node.name == "SemanticUnitIndex"
    )
    methods = {
        node.name for node in index_class.body if isinstance(node, ast.FunctionDef)
    }
    assert {
        "rank_authorized_packed",
        "preflight_authorized_packed",
        "preflight_authorized_top_k_packed",
        "rank_authorized_batch_packed",
        "rank_authorized_top_k_batch_packed",
    } <= methods
