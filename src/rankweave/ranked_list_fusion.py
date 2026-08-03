"""Complete-list fusion for retrieval systems that expose ranked item IDs."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave.score_fusion import (
    _require_positive_integer,
    reciprocal_rank_fusion_score,
)

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)


@dataclass(frozen=True)
class FusedRankedItem(Generic[ItemIdentifier]):
    """One immutable RRF result with its per-channel audit trail."""

    item_id: ItemIdentifier
    score: float
    channel_ranks: tuple[tuple[str, int], ...]


def reciprocal_rank_fuse(
    channel_rankings: Mapping[str, Sequence[ItemIdentifier]],
    *,
    rank_constant_eta: int = 60,
    limit: int | None = None,
) -> list[FusedRankedItem[ItemIdentifier]]:
    """Fuse complete ranked item-ID lists with Reciprocal Rank Fusion.

    Each sequence is interpreted as a one-based ranking. An item may occur
    once per channel and across any number of channels. Results are ordered
    by descending RRF score, with first-seen input order as the deterministic
    tie-breaker. ``channel_ranks`` on each result preserves the evidence used
    to calculate its score.
    """
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    validated_limit = (
        None if limit is None else _require_positive_integer(limit, "limit")
    )

    channel_ranks_by_item: dict[
        ItemIdentifier, list[tuple[str, int]]
    ] = {}
    first_seen_order: dict[ItemIdentifier, int] = {}
    next_first_seen_order = 0

    for channel_name, channel_ranking in channel_rankings.items():
        channel_items_seen: set[ItemIdentifier] = set()
        for one_based_rank, item_id in enumerate(channel_ranking, start=1):
            try:
                hash(item_id)
            except TypeError as exc:
                raise ValueError(
                    f"item at rank {one_based_rank} in channel "
                    f"{channel_name!r} must be hashable"
                ) from exc
            if item_id in channel_items_seen:
                raise ValueError(
                    f"channel {channel_name!r} contains duplicate item "
                    f"{item_id!r}"
                )
            channel_items_seen.add(item_id)
            if item_id not in channel_ranks_by_item:
                channel_ranks_by_item[item_id] = []
                first_seen_order[item_id] = next_first_seen_order
                next_first_seen_order += 1
            channel_ranks_by_item[item_id].append(
                (channel_name, one_based_rank)
            )

    fused_items = [
        FusedRankedItem(
            item_id=item_id,
            score=reciprocal_rank_fusion_score(
                dict(channel_ranks), validated_eta
            ),
            channel_ranks=tuple(channel_ranks),
        )
        for item_id, channel_ranks in channel_ranks_by_item.items()
    ]
    fused_items.sort(
        key=lambda fused_item: (
            -fused_item.score,
            first_seen_order[fused_item.item_id],
        )
    )
    return fused_items if validated_limit is None else fused_items[:validated_limit]
