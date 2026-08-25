from dataclasses import FrozenInstanceError

import pytest

from rankweave import FusedRankedItem, reciprocal_rank_fuse


def test_reciprocal_rank_fuse_combines_complete_ranked_lists():
    fused_items = reciprocal_rank_fuse(
        {
            "lexical": ["doc-a", "doc-b"],
            "dense": ["doc-b", "doc-c"],
        }
    )

    assert [item.item_id for item in fused_items] == ["doc-b", "doc-a", "doc-c"]
    assert fused_items[0].score == pytest.approx(1.0 / 62.0 + 1.0 / 61.0)
    assert fused_items[0].channel_ranks == (("lexical", 2), ("dense", 1))
    assert [
        (
            contribution.channel_name,
            contribution.rank,
            contribution.weight,
            contribution.contribution,
        )
        for contribution in fused_items[0].channel_contributions
    ] == [
        ("lexical", 2, 1.0, pytest.approx(1.0 / 62.0)),
        ("dense", 1, 1.0, pytest.approx(1.0 / 61.0)),
    ]
    assert fused_items[1].score == pytest.approx(1.0 / 61.0)
    assert fused_items[1].channel_ranks == (("lexical", 1),)
    assert fused_items[2].score == pytest.approx(1.0 / 62.0)
    assert fused_items[2].channel_ranks == (("dense", 2),)


def test_reciprocal_rank_fuse_breaks_score_ties_by_first_seen_order():
    fused_items = reciprocal_rank_fuse(
        {
            "lexical": ["first-seen"],
            "dense": ["second-seen"],
        }
    )

    assert [item.item_id for item in fused_items] == [
        "first-seen",
        "second-seen",
    ]


def test_reciprocal_rank_fuse_applies_result_limit():
    fused_items = reciprocal_rank_fuse(
        {
            "lexical": ["doc-a", "doc-b", "doc-c"],
            "dense": ["doc-c", "doc-b", "doc-a"],
        },
        limit=2,
    )

    assert len(fused_items) == 2
    assert [item.item_id for item in fused_items] == ["doc-a", "doc-c"]


@pytest.mark.parametrize("invalid_limit", [0, -1, 1.5, True])
def test_reciprocal_rank_fuse_rejects_invalid_limit(invalid_limit):
    with pytest.raises(ValueError, match="limit"):
        reciprocal_rank_fuse({"lexical": ["doc-a"]}, limit=invalid_limit)


@pytest.mark.parametrize("invalid_eta", [0, 1.5, True])
def test_reciprocal_rank_fuse_rejects_invalid_rank_constant(invalid_eta):
    with pytest.raises(ValueError, match="rank_constant_eta"):
        reciprocal_rank_fuse({}, rank_constant_eta=invalid_eta)


def test_reciprocal_rank_fuse_rejects_duplicate_item_in_one_channel():
    with pytest.raises(ValueError, match="duplicate item"):
        reciprocal_rank_fuse({"lexical": ["doc-a", "doc-a"]})


def test_reciprocal_rank_fuse_rejects_unhashable_item_identifier():
    with pytest.raises(ValueError, match="hashable"):
        reciprocal_rank_fuse({"lexical": [["doc-a"]]})


def test_reciprocal_rank_fuse_accepts_empty_rankings():
    assert reciprocal_rank_fuse({"lexical": [], "dense": []}) == []


def test_fused_ranked_item_is_immutable():
    fused_item = FusedRankedItem(
        item_id="doc-a",
        score=1.0 / 61.0,
        channel_ranks=(("lexical", 1),),
    )

    with pytest.raises(FrozenInstanceError):
        fused_item.score = 0.0
