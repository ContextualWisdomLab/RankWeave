from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    WeightedConvexTuningReport,
    WeightedConvexTuningTrial,
    tune_weighted_convex_fusion,
)
from rankweave.evaluation import AggregateRankingMetrics
from rankweave.tuning import SUPPORTED_TUNING_OBJECTIVES


def _scored_results():
    return {
        "query-a": {
            "lexical": [("a", 1.0), ("b", 0.0)],
            "dense": [("b", 1.0), ("a", 0.0)],
        },
        "query-b": {
            "lexical": [("c", 0.9), ("d", 0.1)],
            "dense": [("d", 0.9), ("c", 0.1)],
        },
    }


def _judgments():
    return {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    }


def _candidate_weights():
    return {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    }


def test_convex_tuning_selects_best_policy_by_mean_ndcg():
    report = tune_weighted_convex_fusion(
        _scored_results(),
        _judgments(),
        _candidate_weights(),
        cutoff=1,
    )

    assert report.best_policy_id == "lexical-heavy"
    assert report.best_channel_weights == (("lexical", 0.9), ("dense", 0.1))
    assert report.best_objective_score == 1.0
    assert [trial.policy_id for trial in report.trials] == [
        "dense-heavy",
        "lexical-heavy",
    ]
    assert [trial.objective_score for trial in report.trials] == [0.0, 1.0]
    assert report.trials[1].evaluation.aggregate == AggregateRankingMetrics(
        query_count=2,
        mean_precision_at_k=1.0,
        mean_recall_at_k=1.0,
        mean_reciprocal_rank_at_k=1.0,
        mean_ndcg_at_k=1.0,
    )


@pytest.mark.parametrize("objective_name", sorted(SUPPORTED_TUNING_OBJECTIVES))
def test_convex_tuning_supports_every_tuning_objective(objective_name):
    report = tune_weighted_convex_fusion(
        _scored_results(),
        _judgments(),
        _candidate_weights(),
        cutoff=1,
        objective_name=objective_name,
    )

    assert report.objective_name == objective_name
    assert report.best_policy_id == "lexical-heavy"
    assert report.best_objective_score == 1.0


def test_convex_tuning_uses_first_policy_as_deterministic_tie_breaker():
    report = tune_weighted_convex_fusion(
        _scored_results(),
        _judgments(),
        {
            "first": {"lexical": 0.5, "dense": 0.5},
            "second": {"lexical": 0.5, "dense": 0.5},
        },
        cutoff=2,
    )

    assert report.best_policy_id == "first"
    assert report.trials[0].objective_score == report.trials[1].objective_score


def test_convex_tuning_rejects_unsupported_objective():
    with pytest.raises(ValueError, match="objective_name must be one of"):
        tune_weighted_convex_fusion(
            _scored_results(),
            _judgments(),
            _candidate_weights(),
            cutoff=1,
            objective_name="mean_map_at_k",
        )


def test_convex_tuning_rejects_empty_candidate_policy_set():
    with pytest.raises(ValueError, match="at least one candidate"):
        tune_weighted_convex_fusion(
            _scored_results(),
            _judgments(),
            {},
            cutoff=1,
        )


def test_convex_tuning_rejects_query_set_mismatch():
    with pytest.raises(ValueError, match="query sets must match"):
        tune_weighted_convex_fusion(
            {"ranked-only": {"dense": [("a", 1.0)]}},
            {"judged-only": {"a": 1}},
            {"policy": {"dense": 1.0}},
            cutoff=1,
        )


def test_convex_tuning_rejects_empty_query_set():
    with pytest.raises(ValueError, match="at least one query"):
        tune_weighted_convex_fusion(
            {},
            {},
            {"policy": {"dense": 1.0}},
            cutoff=1,
        )


def test_convex_tuning_propagates_invalid_weight_policy():
    with pytest.raises(ValueError, match="sum to 1"):
        tune_weighted_convex_fusion(
            _scored_results(),
            _judgments(),
            {"invalid": {"lexical": 0.5, "dense": 0.4}},
            cutoff=1,
        )


@pytest.mark.parametrize("invalid_cutoff", [0, 1.5, True])
def test_convex_tuning_rejects_invalid_cutoff(invalid_cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        tune_weighted_convex_fusion(
            _scored_results(),
            _judgments(),
            _candidate_weights(),
            cutoff=invalid_cutoff,
        )


def test_convex_tuning_propagates_out_of_domain_score():
    scored_results = _scored_results()
    scored_results["query-a"]["lexical"][0] = ("a", 1.1)

    with pytest.raises(ValueError, match=r"score for channel 'lexical'.*\[0, 1\]"):
        tune_weighted_convex_fusion(
            scored_results,
            _judgments(),
            _candidate_weights(),
            cutoff=1,
        )


def test_convex_tuning_propagates_duplicate_item_error():
    scored_results = _scored_results()
    scored_results["query-a"]["lexical"] = [("a", 1.0), ("a", 0.5)]

    with pytest.raises(ValueError, match="contains duplicate item"):
        tune_weighted_convex_fusion(
            scored_results,
            _judgments(),
            _candidate_weights(),
            cutoff=1,
        )


def test_convex_tuning_rejects_result_channel_without_weight():
    scored_results = _scored_results()
    scored_results["query-a"]["graph"] = [("a", 0.8)]

    with pytest.raises(ValueError, match="channels without weights"):
        tune_weighted_convex_fusion(
            scored_results,
            _judgments(),
            _candidate_weights(),
            cutoff=1,
        )


def test_convex_tuning_allows_policy_channel_absent_from_one_query():
    scored_results = _scored_results()
    del scored_results["query-b"]["dense"]

    report = tune_weighted_convex_fusion(
        scored_results,
        _judgments(),
        _candidate_weights(),
        cutoff=1,
    )

    assert report.best_policy_id == "lexical-heavy"


def test_convex_tuning_records_are_immutable_and_exported():
    report = tune_weighted_convex_fusion(
        _scored_results(),
        _judgments(),
        {"policy": {"lexical": 0.5, "dense": 0.5}},
        cutoff=1,
    )
    trial = report.trials[0]

    assert isinstance(trial, WeightedConvexTuningTrial)
    assert isinstance(report, WeightedConvexTuningReport)
    with pytest.raises(FrozenInstanceError):
        trial.objective_score = 0.0
    with pytest.raises(FrozenInstanceError):
        report.best_policy_id = "other"
