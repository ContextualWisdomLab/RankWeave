import math
from dataclasses import FrozenInstanceError

import pytest

from rankweave.evaluation import (
    AggregateRankingMetrics,
    QueryRankingMetrics,
    RankingEvaluationReport,
    RankingMetrics,
    evaluate_ranking,
    evaluate_rankings,
)


def test_evaluate_ranking_computes_hand_checked_metrics():
    metrics = evaluate_ranking(
        ["a", "b", "c", "d"],
        {"a": 3, "c": 1, "x": 2},
        cutoff=3,
    )

    expected_dcg = 7.0 + 1.0 / math.log2(4)
    expected_ideal_dcg = 7.0 + 3.0 / math.log2(3) + 1.0 / math.log2(4)
    assert metrics == RankingMetrics(
        cutoff=3,
        retrieved_count=3,
        relevant_retrieved_count=2,
        total_relevant_count=3,
        precision_at_k=pytest.approx(2.0 / 3.0),
        recall_at_k=pytest.approx(2.0 / 3.0),
        reciprocal_rank_at_k=1.0,
        ndcg_at_k=pytest.approx(expected_dcg / expected_ideal_dcg),
    )


def test_precision_uses_cutoff_denominator_for_short_run():
    metrics = evaluate_ranking(["a"], {"a": 1, "b": 1}, cutoff=5)

    assert metrics.retrieved_count == 1
    assert metrics.precision_at_k == pytest.approx(0.2)
    assert metrics.recall_at_k == pytest.approx(0.5)


def test_unjudged_items_have_zero_relevance():
    metrics = evaluate_ranking(["unknown", "relevant"], {"relevant": 1}, cutoff=2)

    assert metrics.precision_at_k == pytest.approx(0.5)
    assert metrics.reciprocal_rank_at_k == pytest.approx(0.5)


def test_no_positive_judgments_produce_zero_denominator_metrics():
    metrics = evaluate_ranking(["a"], {"a": 0}, cutoff=1)

    assert metrics.total_relevant_count == 0
    assert metrics.recall_at_k == 0.0
    assert metrics.reciprocal_rank_at_k == 0.0
    assert metrics.ndcg_at_k == 0.0


def test_reciprocal_rank_is_bounded_by_cutoff():
    metrics = evaluate_ranking(
        ["a", "b", "c", "d"],
        {"d": 1},
        cutoff=3,
    )

    assert metrics.reciprocal_rank_at_k == 0.0
    assert metrics.recall_at_k == 0.0


def test_evaluate_ranking_rejects_duplicate_items():
    with pytest.raises(ValueError, match="duplicate item"):
        evaluate_ranking(["a", "a"], {"a": 1}, cutoff=2)


def test_evaluate_ranking_rejects_unhashable_items():
    with pytest.raises(ValueError, match="hashable"):
        evaluate_ranking([["a"]], {}, cutoff=1)


@pytest.mark.parametrize("invalid_cutoff", [0, -1, 1.5, True, "10"])
def test_evaluate_ranking_rejects_invalid_cutoff(invalid_cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_ranking([], {}, cutoff=invalid_cutoff)


@pytest.mark.parametrize(
    "invalid_relevance",
    [-1, math.nan, math.inf, -math.inf, True, "1"],
)
def test_evaluate_ranking_rejects_invalid_relevance(invalid_relevance):
    with pytest.raises(ValueError, match="relevance for item 'a'"):
        evaluate_ranking(["a"], {"a": invalid_relevance}, cutoff=1)


def test_evaluate_ranking_rejects_unrepresentable_exponential_gain():
    with pytest.raises(ValueError, match="too large"):
        evaluate_ranking(["a"], {"a": 2048}, cutoff=1)


def test_evaluate_ranking_rejects_unrepresentable_cumulative_gain():
    with pytest.raises(ValueError, match="cumulative gain is too large"):
        evaluate_ranking(
            ["a", "b", "c"],
            {"a": 1023, "b": 1023, "c": 1023},
            cutoff=3,
        )


def test_evaluate_rankings_returns_macro_average_and_query_audit():
    report = evaluate_rankings(
        {
            "query-a": ["a", "b"],
            "query-b": ["x", "y"],
        },
        {
            "query-a": {"a": 1},
            "query-b": {"y": 1},
        },
        cutoff=2,
    )

    assert [entry.query_id for entry in report.query_metrics] == [
        "query-a",
        "query-b",
    ]
    assert report.aggregate == AggregateRankingMetrics(
        query_count=2,
        mean_precision_at_k=pytest.approx(0.5),
        mean_recall_at_k=1.0,
        mean_reciprocal_rank_at_k=pytest.approx(0.75),
        mean_ndcg_at_k=pytest.approx((1.0 + 1.0 / math.log2(3)) / 2.0),
    )


def test_evaluate_rankings_rejects_missing_or_extra_query_ids():
    with pytest.raises(ValueError, match="query sets must match"):
        evaluate_rankings(
            {"ranked-only": []},
            {"judged-only": {}},
            cutoff=1,
        )


def test_evaluate_rankings_rejects_empty_evaluation_set():
    with pytest.raises(ValueError, match="at least one query"):
        evaluate_rankings({}, {}, cutoff=1)


def test_evaluation_records_are_immutable():
    metrics = evaluate_ranking(["a"], {"a": 1}, cutoff=1)
    query_metrics = QueryRankingMetrics("query", metrics)
    aggregate = AggregateRankingMetrics(1, 1.0, 1.0, 1.0, 1.0)
    report = RankingEvaluationReport(1, (query_metrics,), aggregate)

    with pytest.raises(FrozenInstanceError):
        metrics.cutoff = 2
    with pytest.raises(FrozenInstanceError):
        query_metrics.query_id = "other"
    with pytest.raises(FrozenInstanceError):
        aggregate.query_count = 2
    with pytest.raises(FrozenInstanceError):
        report.cutoff = 2
