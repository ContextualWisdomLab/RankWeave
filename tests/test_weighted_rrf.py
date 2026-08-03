import math
from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    FusedWeightedRankedItem,
    WeightedRankContribution,
    weighted_reciprocal_rank_fuse,
    weighted_reciprocal_rank_fusion_score,
)


def test_weighted_rrf_score_combines_rank_contributions():
    score = weighted_reciprocal_rank_fusion_score(
        {"lexical": 2, "dense": 1},
        {"lexical": 0.25, "dense": 0.75},
    )

    assert score == pytest.approx(0.25 / 62.0 + 0.75 / 61.0)


def test_weighted_rrf_score_treats_missing_channel_as_zero():
    score = weighted_reciprocal_rank_fusion_score(
        {"dense": 1},
        {"lexical": 0.25, "dense": 0.75},
    )

    assert score == pytest.approx(0.75 / 61.0)


def test_weighted_rrf_score_accepts_empty_rank_evidence():
    assert weighted_reciprocal_rank_fusion_score(
        {}, {"lexical": 0.25, "dense": 0.75}
    ) == 0.0


def test_weighted_rrf_score_rejects_rank_channel_without_weight():
    with pytest.raises(ValueError, match="without weights"):
        weighted_reciprocal_rank_fusion_score(
            {"unweighted": 1}, {"dense": 1.0}
        )


@pytest.mark.parametrize(
    "invalid_weights",
    [
        {},
        {"dense": 0.9},
        {"dense": -0.1, "lexical": 1.1},
        {"dense": math.nan},
        {"dense": True},
        {"dense": "1.0"},
    ],
)
def test_weighted_rrf_score_rejects_non_convex_weights(invalid_weights):
    with pytest.raises(ValueError):
        weighted_reciprocal_rank_fusion_score({}, invalid_weights)


@pytest.mark.parametrize("invalid_rank", [0, -1, 1.5, True, "1"])
def test_weighted_rrf_score_rejects_invalid_rank(invalid_rank):
    with pytest.raises(ValueError, match="rank for channel 'dense'"):
        weighted_reciprocal_rank_fusion_score(
            {"dense": invalid_rank}, {"dense": 1.0}
        )


@pytest.mark.parametrize("invalid_eta", [0, -1, 1.5, True, "60"])
def test_weighted_rrf_score_rejects_invalid_rank_constant(invalid_eta):
    with pytest.raises(ValueError, match="rank_constant_eta"):
        weighted_reciprocal_rank_fusion_score(
            {"dense": 1}, {"dense": 1.0}, invalid_eta
        )


def test_weighted_reciprocal_rank_fuse_combines_complete_lists():
    fused_items = weighted_reciprocal_rank_fuse(
        {
            "lexical": ["doc-a", "doc-b"],
            "dense": ["doc-b", "doc-c"],
        },
        {"lexical": 0.25, "dense": 0.75},
    )

    assert [item.item_id for item in fused_items] == ["doc-b", "doc-c", "doc-a"]
    assert fused_items[0].score == pytest.approx(0.25 / 62.0 + 0.75 / 61.0)
    assert [
        (
            contribution.channel_name,
            contribution.rank,
            contribution.weight,
        )
        for contribution in fused_items[0].channel_contributions
    ] == [("lexical", 2, 0.25), ("dense", 1, 0.75)]
    assert [
        contribution.contribution
        for contribution in fused_items[0].channel_contributions
    ] == pytest.approx([0.25 / 62.0, 0.75 / 61.0])
    assert [
        (
            contribution.channel_name,
            contribution.rank,
            contribution.contribution,
        )
        for contribution in fused_items[2].channel_contributions
    ] == [("lexical", 1, pytest.approx(0.25 / 61.0)), ("dense", None, 0.0)]


def test_weighted_reciprocal_rank_fuse_breaks_ties_by_first_seen_order():
    fused_items = weighted_reciprocal_rank_fuse(
        {"lexical": ["first-seen"], "dense": ["second-seen"]},
        {"lexical": 0.5, "dense": 0.5},
    )

    assert [item.item_id for item in fused_items] == [
        "first-seen",
        "second-seen",
    ]


def test_weighted_reciprocal_rank_fuse_applies_limit_and_eta():
    fused_items = weighted_reciprocal_rank_fuse(
        {"dense": ["doc-a", "doc-b"]},
        {"dense": 1.0},
        rank_constant_eta=10,
        limit=1,
    )

    assert [item.item_id for item in fused_items] == ["doc-a"]
    assert fused_items[0].score == pytest.approx(1.0 / 11.0)


@pytest.mark.parametrize("invalid_limit", [0, -1, 1.5, True, "1"])
def test_weighted_reciprocal_rank_fuse_rejects_invalid_limit(invalid_limit):
    with pytest.raises(ValueError, match="limit"):
        weighted_reciprocal_rank_fuse(
            {"dense": ["doc-a"]},
            {"dense": 1.0},
            limit=invalid_limit,
        )


def test_weighted_reciprocal_rank_fuse_rejects_unweighted_result_channel():
    with pytest.raises(ValueError, match="without weights"):
        weighted_reciprocal_rank_fuse(
            {"unweighted": []},
            {"dense": 1.0},
        )


def test_weighted_reciprocal_rank_fuse_validates_weights_when_empty():
    with pytest.raises(ValueError, match="sum to 1"):
        weighted_reciprocal_rank_fuse({}, {"dense": 0.9})


def test_weighted_reciprocal_rank_fuse_rejects_duplicate_item():
    with pytest.raises(ValueError, match="duplicate item"):
        weighted_reciprocal_rank_fuse(
            {"dense": ["doc-a", "doc-a"]},
            {"dense": 1.0},
        )


def test_weighted_reciprocal_rank_fuse_rejects_unhashable_item():
    with pytest.raises(ValueError, match="hashable"):
        weighted_reciprocal_rank_fuse(
            {"dense": [["doc-a"]]},
            {"dense": 1.0},
        )


def test_weighted_reciprocal_rank_fuse_accepts_empty_rankings():
    assert weighted_reciprocal_rank_fuse(
        {"lexical": [], "dense": []},
        {"lexical": 0.25, "dense": 0.75},
    ) == []


def test_weighted_rank_audit_records_are_immutable():
    contribution = WeightedRankContribution("dense", 1, 1.0, 1.0 / 61.0)
    fused_item = FusedWeightedRankedItem(
        item_id="doc-a",
        score=1.0 / 61.0,
        channel_contributions=(contribution,),
    )

    with pytest.raises(FrozenInstanceError):
        contribution.weight = 0.5
    with pytest.raises(FrozenInstanceError):
        fused_item.score = 0.0
