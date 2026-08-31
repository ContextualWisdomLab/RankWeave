import random
from dataclasses import FrozenInstanceError

import pytest

from rankweave import FusedRankedItem, ranked_list_fusion, reciprocal_rank_fuse
from rankweave.ranked_list_fusion import lazy_reciprocal_rank_fuse


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
    assert sum(
        contribution.contribution
        for contribution in fused_items[0].channel_contributions
    ) == pytest.approx(fused_items[0].score)
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


def test_bounded_reciprocal_rank_fuse_exactly_matches_full_fusion():
    randomizer = random.Random(7)
    item_ids = [f"doc-{index}" for index in range(500)]
    channels = {}
    for channel_name in ("lexical", "dense", "temporal"):
        ranking = item_ids.copy()
        randomizer.shuffle(ranking)
        channels[channel_name] = ranking

    assert reciprocal_rank_fuse(channels, limit=20) == reciprocal_rank_fuse(channels)[
        :20
    ]


def test_bounded_reciprocal_rank_fuse_materializes_only_requested_hits(monkeypatch):
    materialized = 0

    def counted_fused_item(**kwargs):
        nonlocal materialized
        materialized += 1
        return FusedRankedItem(**kwargs)

    monkeypatch.setattr(ranked_list_fusion, "FusedRankedItem", counted_fused_item)
    result = reciprocal_rank_fuse(
        {
            "lexical": [f"doc-{index}" for index in range(500)],
            "dense": [f"doc-{index}" for index in reversed(range(500))],
        },
        limit=20,
    )

    assert len(result) == 20
    assert materialized == 20


def test_lazy_reciprocal_rank_fuse_matches_full_with_missing_items_and_ties():
    randomizer = random.Random(11)
    item_ids = [f"doc-{index}" for index in range(2000)]
    channels = {}
    for channel_index, channel_name in enumerate(("lexical", "dense", "temporal")):
        ranking = item_ids[channel_index * 100 :].copy()
        randomizer.shuffle(ranking)
        channels[channel_name] = ranking
    ranks = {
        item_id: {
            channel_name: rank
            for channel_name, ranking in channels.items()
            for rank, candidate in enumerate(ranking, start=1)
            if candidate == item_id
        }
        for item_id in item_ids
    }
    first_seen = {}
    for ranking in channels.values():
        for item_id in ranking:
            first_seen.setdefault(item_id, len(first_seen))
    inspected = 0

    def inspected_stream(ranking):
        nonlocal inspected
        for item_id in ranking:
            inspected += 1
            yield item_id

    actual = lazy_reciprocal_rank_fuse(
        {name: inspected_stream(ranking) for name, ranking in channels.items()},
        lambda item_id: (first_seen[item_id], ranks[item_id]),
        limit=20,
    )

    assert actual == reciprocal_rank_fuse(channels)[:20]
    assert inspected < sum(map(len, channels.values()))


def test_lazy_reciprocal_rank_fuse_exhausts_small_overlapping_channels():
    channels = {"first": ["a", "b"], "second": ["b"]}
    resolved = {
        "a": (0, {"first": 1}),
        "b": (1, {"first": 2, "second": 1}),
    }

    assert lazy_reciprocal_rank_fuse(
        channels, resolved.__getitem__, limit=3
    ) == reciprocal_rank_fuse(channels)


@pytest.mark.parametrize(
    ("channels", "resolver", "message"),
    [
        ({"first": [["unhashable"]]}, lambda _item: (0, {}), "hashable"),
        ({"first": ["a"]}, lambda _item: (-1, {"first": 1}), "first-seen"),
    ],
)
def test_lazy_reciprocal_rank_fuse_rejects_invalid_owner_evidence(
    channels, resolver, message
):
    with pytest.raises(ValueError, match=message):
        lazy_reciprocal_rank_fuse(channels, resolver, limit=1)


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
