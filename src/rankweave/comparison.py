"""Paired statistical comparison for retrieval evaluation reports."""

import math
import operator
import random
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import (
    _require_positive_integer,
    _require_unit_interval,
)
from rankweave.evaluation import (
    AggregateRankingMetrics,
    QueryRankingMetrics,
    RankingEvaluationReport,
    RankingMetrics,
    evaluate_rankings,
)

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)

PRECISION_AT_K_METRIC = "precision_at_k"
RECALL_AT_K_METRIC = "recall_at_k"
RECIPROCAL_RANK_AT_K_METRIC = "reciprocal_rank_at_k"
NDCG_AT_K_METRIC = "ndcg_at_k"
SUPPORTED_COMPARISON_METRICS = (
    PRECISION_AT_K_METRIC,
    RECALL_AT_K_METRIC,
    RECIPROCAL_RANK_AT_K_METRIC,
    NDCG_AT_K_METRIC,
)

TWO_SIDED_ALTERNATIVE = "two-sided"
CANDIDATE_GREATER_ALTERNATIVE = "candidate-greater"
CANDIDATE_LESS_ALTERNATIVE = "candidate-less"
SUPPORTED_COMPARISON_ALTERNATIVES = (
    TWO_SIDED_ALTERNATIVE,
    CANDIDATE_GREATER_ALTERNATIVE,
    CANDIDATE_LESS_ALTERNATIVE,
)

EXACT_RANDOMIZATION_METHOD = "exact"
MONTE_CARLO_RANDOMIZATION_METHOD = "monte-carlo"
DEFAULT_RANDOMIZATION_COUNT = 10_000
DEFAULT_RANDOM_SEED = 0
EXACT_RANDOMIZATION_PAIR_LIMIT = 16
_RANDOMIZATION_TOLERANCE = 1e-15


@dataclass(frozen=True)
class QueryMetricDifference(Generic[QueryIdentifier]):
    """One query's aligned baseline, candidate, and difference values."""

    query_id: QueryIdentifier
    baseline_value: float
    candidate_value: float
    difference: float


@dataclass(frozen=True)
class PairedRandomizationResult(Generic[QueryIdentifier]):
    """Auditable paired randomization result for one retrieval metric."""

    metric_name: str
    alternative: str
    query_count: int
    nonzero_difference_count: int
    baseline_mean: float
    candidate_mean: float
    mean_difference: float
    p_value: float
    method: str
    randomizations_evaluated: int
    random_seed: int | None
    query_differences: tuple[QueryMetricDifference[QueryIdentifier], ...]


@dataclass(frozen=True)
class RankingComparisonReport(Generic[QueryIdentifier]):
    """Two complete evaluations and their paired significance comparison."""

    baseline: RankingEvaluationReport[QueryIdentifier]
    candidate: RankingEvaluationReport[QueryIdentifier]
    significance: PairedRandomizationResult[QueryIdentifier]


def _require_supported_value(
    value: str,
    *,
    label: str,
    supported_values: tuple[str, ...],
) -> str:
    """Return a supported string value or raise a stable validation error."""
    if value not in supported_values:
        raise ValueError(f"{label} must be one of {supported_values!r}")
    return value


def _require_integer_seed(value: int) -> int:
    """Return an integer random seed while rejecting booleans and wrong types."""
    if isinstance(value, bool):
        raise ValueError("random_seed must be an integer")
    try:
        return operator.index(value)
    except TypeError as exc:
        raise ValueError("random_seed must be an integer") from exc


def _validated_report_values(
    report: RankingEvaluationReport[QueryIdentifier],
    *,
    label: str,
    metric_name: str,
) -> tuple[int, tuple[QueryIdentifier, ...], dict[QueryIdentifier, float]]:
    """Validate one report and return cutoff, query order, and metric values."""
    if not isinstance(report, RankingEvaluationReport):
        raise ValueError(f"{label} must be RankingEvaluationReport")
    cutoff = _require_positive_integer(report.cutoff, f"{label} cutoff")
    if not report.query_metrics:
        raise ValueError(f"{label} must contain at least one query")
    if not isinstance(report.aggregate, AggregateRankingMetrics):
        raise ValueError(f"{label} aggregate must be AggregateRankingMetrics")
    if report.aggregate.query_count != len(report.query_metrics):
        raise ValueError(
            f"{label} aggregate query_count must equal query metric count"
        )

    query_order: list[QueryIdentifier] = []
    values_by_query: dict[QueryIdentifier, float] = {}
    for entry in report.query_metrics:
        if not isinstance(entry, QueryRankingMetrics):
            raise ValueError(
                f"{label} query metrics must be QueryRankingMetrics values"
            )
        if not isinstance(entry.metrics, RankingMetrics):
            raise ValueError(f"{label} metrics must be RankingMetrics values")
        if entry.metrics.cutoff != cutoff:
            raise ValueError(f"{label} metric cutoff must match report cutoff")
        try:
            if entry.query_id in values_by_query:
                raise ValueError(
                    f"{label} contains duplicate query {entry.query_id!r}"
                )
            metric_value = getattr(entry.metrics, metric_name)
            _require_unit_interval(
                metric_value,
                f"{label} {metric_name} for query {entry.query_id!r}",
            )
            values_by_query[entry.query_id] = float(metric_value)
        except TypeError as exc:
            raise ValueError(f"{label} query identifiers must be hashable") from exc
        query_order.append(entry.query_id)
    return cutoff, tuple(query_order), values_by_query


def _is_extreme(
    permuted_sum: float,
    observed_sum: float,
    alternative: str,
) -> bool:
    """Return whether one randomized signed sum is at least as extreme."""
    if alternative == TWO_SIDED_ALTERNATIVE:
        return abs(permuted_sum) >= abs(observed_sum) - _RANDOMIZATION_TOLERANCE
    if alternative == CANDIDATE_GREATER_ALTERNATIVE:
        return permuted_sum >= observed_sum - _RANDOMIZATION_TOLERANCE
    return permuted_sum <= observed_sum + _RANDOMIZATION_TOLERANCE


def _exact_randomization_p_value(
    differences: tuple[float, ...],
    observed_sum: float,
    alternative: str,
) -> tuple[float, int]:
    """Enumerate every sign assignment and return exact p-value and count."""
    assignment_count = 1 << len(differences)
    extreme_count = 0
    for assignment in range(assignment_count):
        permuted_sum = math.fsum(
            difference if assignment & (1 << index) else -difference
            for index, difference in enumerate(differences)
        )
        if _is_extreme(permuted_sum, observed_sum, alternative):
            extreme_count += 1
    return extreme_count / assignment_count, assignment_count


def _monte_carlo_randomization_p_value(
    differences: tuple[float, ...],
    observed_sum: float,
    alternative: str,
    *,
    randomization_count: int,
    random_seed: int,
) -> float:
    """Return a plus-one-corrected deterministic Monte Carlo p-value."""
    generator = random.Random(random_seed)
    extreme_count = 0
    for _ in range(randomization_count):
        permuted_sum = math.fsum(
            difference if generator.getrandbits(1) else -difference
            for difference in differences
        )
        if _is_extreme(permuted_sum, observed_sum, alternative):
            extreme_count += 1
    return (extreme_count + 1) / (randomization_count + 1)


def compare_ranking_reports(
    baseline_report: RankingEvaluationReport[QueryIdentifier],
    candidate_report: RankingEvaluationReport[QueryIdentifier],
    *,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> PairedRandomizationResult[QueryIdentifier]:
    """Compare two paired retrieval reports with Fisher randomization.

    Query values are aligned by query identifier, never by tuple position. The
    candidate-minus-baseline difference is tested exactly when at most sixteen
    non-zero pairs exist; larger comparisons use deterministic Monte Carlo sign
    randomization with a plus-one p-value correction.
    """
    validated_metric = _require_supported_value(
        metric_name,
        label="metric_name",
        supported_values=SUPPORTED_COMPARISON_METRICS,
    )
    validated_alternative = _require_supported_value(
        alternative,
        label="alternative",
        supported_values=SUPPORTED_COMPARISON_ALTERNATIVES,
    )
    validated_randomization_count = _require_positive_integer(
        randomization_count,
        "randomization_count",
    )
    validated_random_seed = _require_integer_seed(random_seed)
    baseline_cutoff, query_order, baseline_values = _validated_report_values(
        baseline_report,
        label="baseline_report",
        metric_name=validated_metric,
    )
    candidate_cutoff, _, candidate_values = _validated_report_values(
        candidate_report,
        label="candidate_report",
        metric_name=validated_metric,
    )
    if baseline_cutoff != candidate_cutoff:
        raise ValueError("baseline and candidate reports must use the same cutoff")
    if baseline_values.keys() != candidate_values.keys():
        missing_candidate = sorted(
            baseline_values.keys() - candidate_values.keys(),
            key=repr,
        )
        missing_baseline = sorted(
            candidate_values.keys() - baseline_values.keys(),
            key=repr,
        )
        raise ValueError(
            "baseline and candidate query sets must match; "
            f"missing candidate={missing_candidate!r}, "
            f"missing baseline={missing_baseline!r}"
        )

    query_differences = tuple(
        QueryMetricDifference(
            query_id=query_id,
            baseline_value=baseline_values[query_id],
            candidate_value=candidate_values[query_id],
            difference=candidate_values[query_id] - baseline_values[query_id],
        )
        for query_id in query_order
    )
    query_count = len(query_differences)
    baseline_mean = math.fsum(
        difference.baseline_value for difference in query_differences
    ) / query_count
    candidate_mean = math.fsum(
        difference.candidate_value for difference in query_differences
    ) / query_count
    mean_difference = candidate_mean - baseline_mean
    nonzero_differences = tuple(
        difference.difference
        for difference in query_differences
        if difference.difference != 0.0
    )
    observed_sum = math.fsum(nonzero_differences)

    if not nonzero_differences:
        p_value = 1.0
        method = EXACT_RANDOMIZATION_METHOD
        randomizations_evaluated = 1
        reported_seed = None
    elif len(nonzero_differences) <= EXACT_RANDOMIZATION_PAIR_LIMIT:
        p_value, randomizations_evaluated = _exact_randomization_p_value(
            nonzero_differences,
            observed_sum,
            validated_alternative,
        )
        method = EXACT_RANDOMIZATION_METHOD
        reported_seed = None
    else:
        p_value = _monte_carlo_randomization_p_value(
            nonzero_differences,
            observed_sum,
            validated_alternative,
            randomization_count=validated_randomization_count,
            random_seed=validated_random_seed,
        )
        method = MONTE_CARLO_RANDOMIZATION_METHOD
        randomizations_evaluated = validated_randomization_count
        reported_seed = validated_random_seed

    return PairedRandomizationResult(
        metric_name=validated_metric,
        alternative=validated_alternative,
        query_count=query_count,
        nonzero_difference_count=len(nonzero_differences),
        baseline_mean=baseline_mean,
        candidate_mean=candidate_mean,
        mean_difference=mean_difference,
        p_value=p_value,
        method=method,
        randomizations_evaluated=randomizations_evaluated,
        random_seed=reported_seed,
        query_differences=query_differences,
    )


def compare_rankings(
    baseline_rankings_by_query: Mapping[
        QueryIdentifier, Sequence[ItemIdentifier]
    ],
    candidate_rankings_by_query: Mapping[
        QueryIdentifier, Sequence[ItemIdentifier]
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    *,
    cutoff: int,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> RankingComparisonReport[QueryIdentifier]:
    """Evaluate and compare two complete ranking maps on one judged query set."""
    baseline_report = evaluate_rankings(
        baseline_rankings_by_query,
        relevance_by_query,
        cutoff=cutoff,
    )
    candidate_report = evaluate_rankings(
        candidate_rankings_by_query,
        relevance_by_query,
        cutoff=cutoff,
    )
    significance = compare_ranking_reports(
        baseline_report,
        candidate_report,
        metric_name=metric_name,
        alternative=alternative,
        randomization_count=randomization_count,
        random_seed=random_seed,
    )
    return RankingComparisonReport(
        baseline=baseline_report,
        candidate=candidate_report,
        significance=significance,
    )
