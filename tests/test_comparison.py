import math
from dataclasses import FrozenInstanceError

import pytest

from rankweave.comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    CANDIDATE_LESS_ALTERNATIVE,
    EXACT_RANDOMIZATION_METHOD,
    MONTE_CARLO_RANDOMIZATION_METHOD,
    TWO_SIDED_ALTERNATIVE,
    PairedRandomizationResult,
    QueryMetricDifference,
    RankingComparisonReport,
    compare_ranking_reports,
    compare_rankings,
)
from rankweave.evaluation import (
    AggregateRankingMetrics,
    QueryRankingMetrics,
    RankingEvaluationReport,
    RankingMetrics,
)


def _ranking_metrics(value, *, cutoff=1):
    return RankingMetrics(
        cutoff=cutoff,
        retrieved_count=cutoff,
        relevant_retrieved_count=0,
        total_relevant_count=0,
        precision_at_k=value,
        recall_at_k=value,
        reciprocal_rank_at_k=value,
        ndcg_at_k=value,
    )


def _report(
    query_values,
    *,
    cutoff=1,
    metric_cutoff=None,
    aggregate_query_count=None,
):
    entries = tuple(
        QueryRankingMetrics(
            query_id,
            _ranking_metrics(
                value,
                cutoff=cutoff if metric_cutoff is None else metric_cutoff,
            ),
        )
        for query_id, value in query_values
    )
    mean_value = math.fsum(value for _, value in query_values) / len(query_values)
    query_count = (
        len(entries) if aggregate_query_count is None else aggregate_query_count
    )
    return RankingEvaluationReport(
        cutoff=cutoff,
        query_metrics=entries,
        aggregate=AggregateRankingMetrics(
            query_count=query_count,
            mean_precision_at_k=mean_value,
            mean_recall_at_k=mean_value,
            mean_reciprocal_rank_at_k=mean_value,
            mean_ndcg_at_k=mean_value,
        ),
    )


def test_exact_randomization_computes_hand_checked_alternatives():
    baseline = _report((("query-a", 0.0), ("query-b", 0.5)))
    candidate = _report((("query-a", 1.0), ("query-b", 0.0)))

    two_sided = compare_ranking_reports(baseline, candidate)
    greater = compare_ranking_reports(
        baseline,
        candidate,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
    )
    less = compare_ranking_reports(
        baseline,
        candidate,
        alternative=CANDIDATE_LESS_ALTERNATIVE,
    )

    assert two_sided.alternative == TWO_SIDED_ALTERNATIVE
    assert two_sided.method == EXACT_RANDOMIZATION_METHOD
    assert two_sided.randomizations_evaluated == 4
    assert two_sided.baseline_mean == pytest.approx(0.25)
    assert two_sided.candidate_mean == pytest.approx(0.5)
    assert two_sided.mean_difference == pytest.approx(0.25)
    assert two_sided.p_value == 1.0
    assert greater.p_value == pytest.approx(0.5)
    assert less.p_value == pytest.approx(0.75)


def test_comparison_aligns_candidate_values_by_query_id():
    baseline = _report((("query-a", 0.1), ("query-b", 0.2)))
    candidate = _report((("query-b", 0.6), ("query-a", 0.4)))

    result = compare_ranking_reports(baseline, candidate)

    assert result.query_differences == (
        QueryMetricDifference("query-a", 0.1, 0.4, pytest.approx(0.3)),
        QueryMetricDifference("query-b", 0.2, 0.6, pytest.approx(0.4)),
    )


def test_all_zero_differences_return_exact_probability_one():
    report = _report((("query-a", 0.2), ("query-b", 0.8)))

    result = compare_ranking_reports(report, report)

    assert result.nonzero_difference_count == 0
    assert result.method == EXACT_RANDOMIZATION_METHOD
    assert result.randomizations_evaluated == 1
    assert result.mean_difference == 0.0
    assert result.p_value == 1.0
    assert result.random_seed is None


def test_sixteen_nonzero_pairs_use_exact_enumeration():
    baseline = _report(tuple((f"query-{index}", 0.4) for index in range(16)))
    candidate = _report(tuple((f"query-{index}", 0.5) for index in range(16)))

    result = compare_ranking_reports(baseline, candidate)

    assert result.method == EXACT_RANDOMIZATION_METHOD
    assert result.randomizations_evaluated == 65_536
    assert result.nonzero_difference_count == 16


def test_monte_carlo_is_deterministic_for_the_same_seed():
    baseline = _report(tuple((f"query-{index}", 0.4) for index in range(17)))
    candidate = _report(tuple((f"query-{index}", 0.5) for index in range(17)))

    first = compare_ranking_reports(
        baseline,
        candidate,
        randomization_count=250,
        random_seed=7,
    )
    second = compare_ranking_reports(
        baseline,
        candidate,
        randomization_count=250,
        random_seed=7,
    )

    assert first == second
    assert first.method == MONTE_CARLO_RANDOMIZATION_METHOD
    assert first.randomizations_evaluated == 250
    assert first.random_seed == 7
    assert 0.0 < first.p_value <= 1.0


def test_compare_rankings_evaluates_and_compares_complete_query_sets():
    report = compare_rankings(
        {
            "query-a": ["irrelevant", "relevant-a"],
            "query-b": ["irrelevant", "relevant-b"],
        },
        {
            "query-a": ["relevant-a", "irrelevant"],
            "query-b": ["relevant-b", "irrelevant"],
        },
        {
            "query-a": {"relevant-a": 1},
            "query-b": {"relevant-b": 1},
        },
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
    )

    assert isinstance(report, RankingComparisonReport)
    assert report.baseline.aggregate.mean_ndcg_at_k == 0.0
    assert report.candidate.aggregate.mean_ndcg_at_k == 1.0
    assert report.significance.mean_difference == 1.0
    assert report.significance.p_value == pytest.approx(0.25)


@pytest.mark.parametrize(
    "metric_name",
    [
        "precision_at_k",
        "recall_at_k",
        "reciprocal_rank_at_k",
        "ndcg_at_k",
    ],
)
def test_all_documented_metrics_are_supported(metric_name):
    baseline = _report((("query", 0.25),))
    candidate = _report((("query", 0.75),))

    result = compare_ranking_reports(
        baseline,
        candidate,
        metric_name=metric_name,
    )

    assert result.metric_name == metric_name
    assert result.mean_difference == pytest.approx(0.5)


def test_comparison_records_are_immutable():
    result = compare_ranking_reports(
        _report((("query", 0.25),)),
        _report((("query", 0.75),)),
    )
    comparison = RankingComparisonReport(
        baseline=_report((("query", 0.25),)),
        candidate=_report((("query", 0.75),)),
        significance=result,
    )

    assert isinstance(result, PairedRandomizationResult)
    with pytest.raises(FrozenInstanceError):
        result.p_value = 0.0
    with pytest.raises(FrozenInstanceError):
        result.query_differences[0].difference = 0.0
    with pytest.raises(FrozenInstanceError):
        comparison.significance = result


@pytest.mark.parametrize("invalid_report", [None, object()])
def test_comparison_rejects_wrong_report_types(invalid_report):
    valid = _report((("query", 0.5),))
    with pytest.raises(ValueError, match="RankingEvaluationReport"):
        compare_ranking_reports(invalid_report, valid)
    with pytest.raises(ValueError, match="RankingEvaluationReport"):
        compare_ranking_reports(valid, invalid_report)


def test_comparison_rejects_empty_report():
    empty = RankingEvaluationReport(
        cutoff=1,
        query_metrics=(),
        aggregate=AggregateRankingMetrics(0, 0.0, 0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="at least one query"):
        compare_ranking_reports(empty, empty)


def test_comparison_rejects_cutoff_or_query_set_mismatch():
    baseline = _report((("query-a", 0.5),), cutoff=1)
    with pytest.raises(ValueError, match="same cutoff"):
        compare_ranking_reports(
            baseline,
            _report((("query-a", 0.5),), cutoff=2),
        )
    with pytest.raises(ValueError, match="query sets must match"):
        compare_ranking_reports(
            baseline,
            _report((("query-b", 0.5),), cutoff=1),
        )


def test_comparison_rejects_duplicate_or_unhashable_query_ids():
    valid = _report((("query", 0.5),))
    duplicate = _report((("query", 0.4), ("query", 0.5)))
    unhashable = _report(((["query"], 0.5),))

    with pytest.raises(ValueError, match="duplicate query"):
        compare_ranking_reports(duplicate, valid)
    with pytest.raises(ValueError, match="hashable"):
        compare_ranking_reports(unhashable, unhashable)


def test_comparison_rejects_inconsistent_report_structure():
    valid = _report((("query", 0.5),))
    with pytest.raises(ValueError, match="aggregate query_count"):
        compare_ranking_reports(
            _report((("query", 0.5),), aggregate_query_count=2),
            valid,
        )
    with pytest.raises(ValueError, match="metric cutoff"):
        compare_ranking_reports(
            _report((("query", 0.5),), cutoff=1, metric_cutoff=2),
            valid,
        )


@pytest.mark.parametrize("invalid_value", [-0.1, 1.1, math.nan, math.inf])
def test_comparison_rejects_metric_values_outside_unit_interval(invalid_value):
    with pytest.raises(ValueError, match="within \[0, 1\]"):
        compare_ranking_reports(
            _report((("query", invalid_value),)),
            _report((("query", 0.5),)),
        )


def test_comparison_rejects_unsupported_metric_or_alternative():
    baseline = _report((("query", 0.5),))
    candidate = _report((("query", 0.6),))
    with pytest.raises(ValueError, match="metric_name must be one of"):
        compare_ranking_reports(
            baseline,
            candidate,
            metric_name="average_precision",
        )
    with pytest.raises(ValueError, match="alternative must be one of"):
        compare_ranking_reports(
            baseline,
            candidate,
            alternative="greater",
        )


@pytest.mark.parametrize("invalid_count", [0, -1, 1.5, True, "100"])
def test_comparison_rejects_invalid_randomization_count(invalid_count):
    with pytest.raises(ValueError, match="randomization_count"):
        compare_ranking_reports(
            _report((("query", 0.5),)),
            _report((("query", 0.6),)),
            randomization_count=invalid_count,
        )


@pytest.mark.parametrize("invalid_seed", [1.5, True, "7"])
def test_comparison_rejects_invalid_random_seed(invalid_seed):
    with pytest.raises(ValueError, match="random_seed must be an integer"):
        compare_ranking_reports(
            _report((("query", 0.5),)),
            _report((("query", 0.6),)),
            random_seed=invalid_seed,
        )
