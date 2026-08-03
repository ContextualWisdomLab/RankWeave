"""Dependency-free effectiveness evaluation for ranked retrieval results."""

import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_finite, _require_positive_integer

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)


@dataclass(frozen=True)
class RankingMetrics:
    """Effectiveness metrics for one ranking at one cutoff."""

    cutoff: int
    retrieved_count: int
    relevant_retrieved_count: int
    total_relevant_count: int
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank_at_k: float
    ndcg_at_k: float


@dataclass(frozen=True)
class QueryRankingMetrics(Generic[QueryIdentifier]):
    """One query identifier paired with its immutable metrics."""

    query_id: QueryIdentifier
    metrics: RankingMetrics


@dataclass(frozen=True)
class AggregateRankingMetrics:
    """Macro-averaged effectiveness metrics over an evaluation query set."""

    query_count: int
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank_at_k: float
    mean_ndcg_at_k: float


@dataclass(frozen=True)
class RankingEvaluationReport(Generic[QueryIdentifier]):
    """Per-query metrics and macro averages for a complete evaluation run."""

    cutoff: int
    query_metrics: tuple[QueryRankingMetrics[QueryIdentifier], ...]
    aggregate: AggregateRankingMetrics


def _validate_ranking(
    ranked_items: Sequence[ItemIdentifier],
) -> tuple[ItemIdentifier, ...]:
    """Return a unique, hashable ranking as an immutable tuple."""
    validated_items: list[ItemIdentifier] = []
    seen_items: set[ItemIdentifier] = set()
    for one_based_rank, item_id in enumerate(ranked_items, start=1):
        try:
            if item_id in seen_items:
                raise ValueError(
                    f"ranking contains duplicate item {item_id!r} at rank "
                    f"{one_based_rank}"
                )
            seen_items.add(item_id)
        except TypeError as exc:
            raise ValueError(
                f"item at rank {one_based_rank} must be hashable"
            ) from exc
        validated_items.append(item_id)
    return tuple(validated_items)


def _validate_relevance_judgments(
    relevance_by_item: Mapping[ItemIdentifier, float],
) -> dict[ItemIdentifier, float]:
    """Return finite non-negative relevance grades as ordinary floats."""
    validated_relevance: dict[ItemIdentifier, float] = {}
    for item_id, relevance_grade in relevance_by_item.items():
        label = f"relevance for item {item_id!r}"
        _require_finite(relevance_grade, label)
        if relevance_grade < 0.0:
            raise ValueError(f"{label} must be non-negative")
        validated_relevance[item_id] = float(relevance_grade)
    return validated_relevance


def _exponential_gain(relevance_grade: float) -> float:
    """Return the standard graded-relevance gain ``2**grade - 1``."""
    try:
        gain = math.pow(2.0, relevance_grade) - 1.0
    except OverflowError as exc:
        raise ValueError(
            "relevance grade is too large for exponential gain"
        ) from exc
    return gain


def _discounted_cumulative_gain(relevance_grades: Sequence[float]) -> float:
    """Return DCG with logarithmic rank discount and exponential gains."""
    return math.fsum(
        _exponential_gain(relevance_grade) / math.log2(one_based_rank + 1)
        for one_based_rank, relevance_grade in enumerate(
            relevance_grades, start=1
        )
    )


def evaluate_ranking(
    ranked_items: Sequence[ItemIdentifier],
    relevance_by_item: Mapping[ItemIdentifier, float],
    *,
    cutoff: int,
) -> RankingMetrics:
    """Evaluate one ranking with precision, recall, RR, and nDCG at ``cutoff``.

    Positive relevance grades are treated as relevant for binary metrics.
    Unjudged items receive grade zero. Precision uses the requested cutoff as
    its denominator, so short result lists are penalized consistently with
    standard precision-at-k evaluation. Reciprocal rank is also cutoff-bound.
    nDCG uses exponential gains and logarithmic discounting.
    """
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    validated_ranking = _validate_ranking(ranked_items)
    validated_relevance = _validate_relevance_judgments(relevance_by_item)
    top_items = validated_ranking[:validated_cutoff]
    top_relevance = tuple(
        validated_relevance.get(item_id, 0.0) for item_id in top_items
    )

    total_relevant_count = sum(
        relevance_grade > 0.0
        for relevance_grade in validated_relevance.values()
    )
    relevant_retrieved_count = sum(
        relevance_grade > 0.0 for relevance_grade in top_relevance
    )
    precision_at_k = relevant_retrieved_count / validated_cutoff
    recall_at_k = (
        relevant_retrieved_count / total_relevant_count
        if total_relevant_count
        else 0.0
    )
    reciprocal_rank_at_k = next(
        (
            1.0 / one_based_rank
            for one_based_rank, relevance_grade in enumerate(
                top_relevance, start=1
            )
            if relevance_grade > 0.0
        ),
        0.0,
    )

    discounted_gain = _discounted_cumulative_gain(top_relevance)
    ideal_relevance = tuple(
        sorted(validated_relevance.values(), reverse=True)[:validated_cutoff]
    )
    ideal_discounted_gain = _discounted_cumulative_gain(ideal_relevance)
    ndcg_at_k = (
        discounted_gain / ideal_discounted_gain
        if ideal_discounted_gain
        else 0.0
    )

    return RankingMetrics(
        cutoff=validated_cutoff,
        retrieved_count=len(top_items),
        relevant_retrieved_count=relevant_retrieved_count,
        total_relevant_count=total_relevant_count,
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        reciprocal_rank_at_k=reciprocal_rank_at_k,
        ndcg_at_k=ndcg_at_k,
    )


def evaluate_rankings(
    rankings_by_query: Mapping[
        QueryIdentifier, Sequence[ItemIdentifier]
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    *,
    cutoff: int,
) -> RankingEvaluationReport[QueryIdentifier]:
    """Evaluate a complete query set and return per-query plus macro metrics.

    The ranking and relevance mappings must contain exactly the same query
    identifiers. Represent an intentionally empty run with an empty sequence
    for that query rather than omitting its key; this prevents silent metric
    inflation from accidentally dropped queries.
    """
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    ranking_query_ids = set(rankings_by_query)
    relevance_query_ids = set(relevance_by_query)
    if not ranking_query_ids and not relevance_query_ids:
        raise ValueError("evaluation requires at least one query")
    if ranking_query_ids != relevance_query_ids:
        missing_rankings = sorted(
            relevance_query_ids - ranking_query_ids, key=repr
        )
        missing_judgments = sorted(
            ranking_query_ids - relevance_query_ids, key=repr
        )
        raise ValueError(
            "ranking and relevance query sets must match; "
            f"missing rankings={missing_rankings!r}, "
            f"missing judgments={missing_judgments!r}"
        )

    query_metrics = tuple(
        QueryRankingMetrics(
            query_id=query_id,
            metrics=evaluate_ranking(
                ranked_items,
                relevance_by_query[query_id],
                cutoff=validated_cutoff,
            ),
        )
        for query_id, ranked_items in rankings_by_query.items()
    )
    query_count = len(query_metrics)
    aggregate = AggregateRankingMetrics(
        query_count=query_count,
        mean_precision_at_k=math.fsum(
            entry.metrics.precision_at_k for entry in query_metrics
        )
        / query_count,
        mean_recall_at_k=math.fsum(
            entry.metrics.recall_at_k for entry in query_metrics
        )
        / query_count,
        mean_reciprocal_rank_at_k=math.fsum(
            entry.metrics.reciprocal_rank_at_k for entry in query_metrics
        )
        / query_count,
        mean_ndcg_at_k=math.fsum(
            entry.metrics.ndcg_at_k for entry in query_metrics
        )
        / query_count,
    )
    return RankingEvaluationReport(
        cutoff=validated_cutoff,
        query_metrics=query_metrics,
        aggregate=aggregate,
    )
