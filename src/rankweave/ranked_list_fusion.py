"""Complete-list fusion for retrieval systems that expose ranked item IDs."""

import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.score_fusion import (
    _validate_convex_weights,
    reciprocal_rank_fusion_score,
    weighted_convex_combination_score,
)

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)


def _register_channel_item(
    item_id: ItemIdentifier,
    channel_items_seen: set[ItemIdentifier],
    *,
    channel_name: str,
    position_label: str,
    position: int,
) -> None:
    """Validate hashability and register one unique per-channel item ID."""
    try:
        if item_id in channel_items_seen:
            raise ValueError(
                f"channel {channel_name!r} contains duplicate item {item_id!r}"
            )
        channel_items_seen.add(item_id)
    except TypeError as exc:
        raise ValueError(
            f"item at {position_label} {position} in channel "
            f"{channel_name!r} must be hashable"
        ) from exc


def _collect_channel_ranks(
    channel_rankings: Mapping[str, Sequence[ItemIdentifier]],
) -> tuple[
    dict[ItemIdentifier, list[tuple[str, int]]],
    dict[ItemIdentifier, int],
]:
    """Collect per-item ranks and deterministic first-seen positions."""
    channel_ranks_by_item: dict[
        ItemIdentifier, list[tuple[str, int]]
    ] = {}
    first_seen_order: dict[ItemIdentifier, int] = {}
    next_first_seen_order = 0

    for channel_name, channel_ranking in channel_rankings.items():
        channel_items_seen: set[ItemIdentifier] = set()
        for one_based_rank, item_id in enumerate(channel_ranking, start=1):
            _register_channel_item(
                item_id,
                channel_items_seen,
                channel_name=channel_name,
                position_label="rank",
                position=one_based_rank,
            )
            if item_id not in channel_ranks_by_item:
                channel_ranks_by_item[item_id] = []
                first_seen_order[item_id] = next_first_seen_order
                next_first_seen_order += 1
            channel_ranks_by_item[item_id].append(
                (channel_name, one_based_rank)
            )

    return channel_ranks_by_item, first_seen_order


def _build_weighted_channel_contribution(
    channel_name: str,
    channel_score: float | None,
    channel_weight: float,
) -> "WeightedChannelContribution":
    """Build one weighted score contribution, treating absence as zero."""
    score_or_infimum = 0.0 if channel_score is None else channel_score
    return WeightedChannelContribution(
        channel_name=channel_name,
        score=channel_score,
        weight=channel_weight,
        contribution=channel_weight * score_or_infimum,
    )


def _build_weighted_rank_contribution(
    channel_name: str,
    one_based_rank: int | None,
    channel_weight: float,
    rank_constant_eta: int,
) -> "WeightedRankContribution":
    """Build one weighted reciprocal-rank contribution or zero if absent."""
    contribution = (
        0.0
        if one_based_rank is None
        else channel_weight / (rank_constant_eta + one_based_rank)
    )
    return WeightedRankContribution(
        channel_name=channel_name,
        rank=one_based_rank,
        weight=channel_weight,
        contribution=contribution,
    )


@dataclass(frozen=True)
class WeightedChannelContribution:
    """One channel's normalized score, weight, and fused contribution."""

    channel_name: str
    score: float | None
    weight: float
    contribution: float


@dataclass(frozen=True)
class WeightedRankContribution:
    """One channel's rank, weight, and weighted reciprocal contribution."""

    channel_name: str
    rank: int | None
    weight: float
    contribution: float


@dataclass(frozen=True)
class FusedScoredItem(Generic[ItemIdentifier]):
    """One immutable weighted-fusion result with channel contributions."""

    item_id: ItemIdentifier
    score: float
    channel_contributions: tuple[WeightedChannelContribution, ...]


@dataclass(frozen=True)
class FusedRankedItem(Generic[ItemIdentifier]):
    """One immutable RRF result with its per-channel audit trail."""

    item_id: ItemIdentifier
    score: float
    channel_ranks: tuple[tuple[str, int], ...]
    channel_contributions: tuple[WeightedRankContribution, ...] = ()


@dataclass(frozen=True)
class FusedWeightedRankedItem(Generic[ItemIdentifier]):
    """One immutable weighted-RRF result with channel contributions."""

    item_id: ItemIdentifier
    score: float
    channel_contributions: tuple[WeightedRankContribution, ...]


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
    tie-breaker. ``channel_ranks`` and ``channel_contributions`` preserve the
    exact owned ranks and Cormack summands used to calculate each score.
    """
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    validated_limit = (
        None if limit is None else _require_positive_integer(limit, "limit")
    )
    channel_ranks_by_item, first_seen_order = _collect_channel_ranks(
        channel_rankings
    )

    fused_items = [
        FusedRankedItem(
            item_id=item_id,
            score=reciprocal_rank_fusion_score(
                dict(channel_ranks), validated_eta
            ),
            channel_ranks=tuple(channel_ranks),
            channel_contributions=tuple(
                _build_weighted_rank_contribution(
                    channel_name,
                    one_based_rank,
                    1.0,
                    validated_eta,
                )
                for channel_name, one_based_rank in channel_ranks
            ),
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


def weighted_reciprocal_rank_fuse(
    channel_rankings: Mapping[str, Sequence[ItemIdentifier]],
    channel_weights: Mapping[str, float],
    *,
    rank_constant_eta: int = 60,
    limit: int | None = None,
) -> list[FusedWeightedRankedItem[ItemIdentifier]]:
    """Fuse complete ranked lists with fixed convex channel weights.

    ``channel_weights`` defines the complete channel set and must sum to one.
    A missing item in a channel contributes zero. Results use deterministic
    first-seen tie-breaking and expose every channel's rank, weight, and
    contribution, including absent evidence represented by ``rank=None``.
    The caller supplies one fixed reliability policy for the whole call;
    RankWeave does not infer query- or item-adaptive weights.
    """
    result_channels_without_weights = set(channel_rankings) - set(
        channel_weights
    )
    if result_channels_without_weights:
        raise ValueError(
            "channel ranks contain channels without weights: "
            f"{sorted(result_channels_without_weights)!r}"
        )
    _validate_convex_weights(channel_weights)
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    validated_limit = (
        None if limit is None else _require_positive_integer(limit, "limit")
    )
    channel_ranks_by_item, first_seen_order = _collect_channel_ranks(
        channel_rankings
    )

    fused_items = []
    for item_id, channel_ranks in channel_ranks_by_item.items():
        rank_by_channel = dict(channel_ranks)
        channel_contributions = tuple(
            _build_weighted_rank_contribution(
                channel_name,
                rank_by_channel.get(channel_name),
                channel_weight,
                validated_eta,
            )
            for channel_name, channel_weight in channel_weights.items()
        )
        fused_items.append(
            FusedWeightedRankedItem(
                item_id=item_id,
                score=math.fsum(
                    contribution.contribution
                    for contribution in channel_contributions
                ),
                channel_contributions=channel_contributions,
            )
        )

    fused_items.sort(
        key=lambda fused_item: (
            -fused_item.score,
            first_seen_order[fused_item.item_id],
        )
    )
    return fused_items if validated_limit is None else fused_items[:validated_limit]


def weighted_convex_fuse(
    channel_results: Mapping[
        str, Sequence[tuple[ItemIdentifier, float]]
    ],
    channel_weights: Mapping[str, float],
    *,
    limit: int | None = None,
) -> list[FusedScoredItem[ItemIdentifier]]:
    """Fuse complete normalized-score result lists with convex weights.

    Each channel supplies ``(item_id, score)`` pairs with scores in ``[0, 1]``.
    The union of item identifiers is fused using the complete channel-weight
    mapping; missing channel evidence contributes zero. Results are ordered by
    descending fused score, with first-seen input order as the deterministic
    tie-breaker. Every result includes all channel contributions for audit.
    """
    result_channels_without_weights = set(channel_results) - set(
        channel_weights
    )
    if result_channels_without_weights:
        raise ValueError(
            "channel scores contain channels without weights: "
            f"{sorted(result_channels_without_weights)!r}"
        )
    weighted_convex_combination_score({}, channel_weights)
    validated_limit = (
        None if limit is None else _require_positive_integer(limit, "limit")
    )

    channel_scores_by_item: dict[ItemIdentifier, dict[str, float]] = {}
    first_seen_order: dict[ItemIdentifier, int] = {}
    next_first_seen_order = 0

    for channel_name, channel_items in channel_results.items():
        channel_items_seen: set[ItemIdentifier] = set()
        for result_position, (item_id, channel_score) in enumerate(
            channel_items, start=1
        ):
            _register_channel_item(
                item_id,
                channel_items_seen,
                channel_name=channel_name,
                position_label="position",
                position=result_position,
            )
            if channel_score is None:
                raise ValueError(
                    f"score for channel {channel_name!r} must be provided"
                )
            if item_id not in channel_scores_by_item:
                channel_scores_by_item[item_id] = {}
                first_seen_order[item_id] = next_first_seen_order
                next_first_seen_order += 1
            channel_scores_by_item[item_id][channel_name] = channel_score

    fused_items = []
    for item_id, channel_scores in channel_scores_by_item.items():
        fused_score = weighted_convex_combination_score(
            channel_scores, channel_weights
        )
        channel_contributions = tuple(
            _build_weighted_channel_contribution(
                channel_name,
                channel_scores.get(channel_name),
                channel_weight,
            )
            for channel_name, channel_weight in channel_weights.items()
        )
        fused_items.append(
            FusedScoredItem(
                item_id=item_id,
                score=fused_score,
                channel_contributions=channel_contributions,
            )
        )

    fused_items.sort(
        key=lambda fused_item: (
            -fused_item.score,
            first_seen_order[fused_item.item_id],
        )
    )
    return fused_items if validated_limit is None else fused_items[:validated_limit]
