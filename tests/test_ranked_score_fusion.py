import math
from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    FusedScoredItem,
    WeightedChannelContribution,
    weighted_convex_fuse,
)


def test_weighted_convex_fuse_combines_complete_scored_lists():
    fused_items = weighted_convex_fuse(
        {
            "semantic": [("doc-b", 0.9), ("doc-a", 0.5)],
            "lexical": [("doc-a", 0.8), ("doc-c", 0.7)],
        },
        {"semantic": 0.6, "lexical": 0.4},
    )

    assert [item.item_id for item in fused_items] == ["doc-a", "doc-b", "doc-c"]
    assert fused_items[0].score == pytest.approx(0.62)
    assert [
        (item.channel_name, item.score, item.weight)
        for item in fused_items[0].channel_contributions
    ] == [("semantic", 0.5, 0.6), ("lexical", 0.8, 0.4)]
    assert [
        item.contribution for item in fused_items[0].channel_contributions
    ] == pytest.approx([0.3, 0.32])
    assert fused_items[1].score == pytest.approx(0.54)
    assert [
        (item.channel_name, item.score, item.weight)
        for item in fused_items[1].channel_contributions
    ] == [("semantic", 0.9, 0.6), ("lexical", None, 0.4)]
    assert [
        item.contribution for item in fused_items[1].channel_contributions
    ] == pytest.approx([0.54, 0.0])
    assert fused_items[2].score == pytest.approx(0.28)


def test_weighted_convex_fuse_breaks_score_ties_by_first_seen_order():
    fused_items = weighted_convex_fuse(
        {
            "semantic": [("first-seen", 0.5)],
            "lexical": [("second-seen", 0.5)],
        },
        {"semantic": 0.5, "lexical": 0.5},
    )

    assert [item.item_id for item in fused_items] == [
        "first-seen",
        "second-seen",
    ]


def test_weighted_convex_fuse_applies_result_limit():
    fused_items = weighted_convex_fuse(
        {"semantic": [("doc-a", 0.9), ("doc-b", 0.8)]},
        {"semantic": 1.0},
        limit=1,
    )

    assert [item.item_id for item in fused_items] == ["doc-a"]


@pytest.mark.parametrize("invalid_limit", [0, -1, 1.5, True])
def test_weighted_convex_fuse_rejects_invalid_limit(invalid_limit):
    with pytest.raises(ValueError, match="limit"):
        weighted_convex_fuse(
            {"semantic": [("doc-a", 0.9)]},
            {"semantic": 1.0},
            limit=invalid_limit,
        )


def test_weighted_convex_fuse_rejects_result_channel_without_weight():
    with pytest.raises(ValueError, match="without weights"):
        weighted_convex_fuse(
            {"unweighted": []},
            {"semantic": 1.0},
        )


@pytest.mark.parametrize(
    "invalid_weights",
    [
        {"semantic": 0.9},
        {"semantic": -0.1, "lexical": 1.1},
        {"semantic": math.nan},
    ],
)
def test_weighted_convex_fuse_validates_weights_without_candidates(
    invalid_weights,
):
    with pytest.raises(ValueError):
        weighted_convex_fuse({}, invalid_weights)


@pytest.mark.parametrize("invalid_score", [-0.1, 1.1, math.nan])
def test_weighted_convex_fuse_rejects_invalid_score(invalid_score):
    with pytest.raises(ValueError, match="score for channel 'semantic'"):
        weighted_convex_fuse(
            {"semantic": [("doc-a", invalid_score)]},
            {"semantic": 1.0},
        )


def test_weighted_convex_fuse_rejects_missing_score_value():
    with pytest.raises(ValueError, match="score.*must be provided"):
        weighted_convex_fuse(
            {"semantic": [("doc-a", None)]},
            {"semantic": 1.0},
        )


def test_weighted_convex_fuse_rejects_duplicate_item_in_one_channel():
    with pytest.raises(ValueError, match="duplicate item"):
        weighted_convex_fuse(
            {"semantic": [("doc-a", 0.9), ("doc-a", 0.8)]},
            {"semantic": 1.0},
        )


def test_weighted_convex_fuse_rejects_unhashable_item_identifier():
    with pytest.raises(ValueError, match="hashable"):
        weighted_convex_fuse(
            {"semantic": [(["doc-a"], 0.9)]},
            {"semantic": 1.0},
        )


def test_weighted_convex_fuse_accepts_empty_results():
    assert weighted_convex_fuse(
        {"semantic": [], "lexical": []},
        {"semantic": 0.6, "lexical": 0.4},
    ) == []


def test_weighted_fusion_audit_records_are_immutable():
    contribution = WeightedChannelContribution("semantic", 0.9, 1.0, 0.9)
    fused_item = FusedScoredItem(
        item_id="doc-a",
        score=0.9,
        channel_contributions=(contribution,),
    )

    with pytest.raises(FrozenInstanceError):
        contribution.weight = 0.5
    with pytest.raises(FrozenInstanceError):
        fused_item.score = 0.0
