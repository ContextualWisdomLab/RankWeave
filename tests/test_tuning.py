from dataclasses import FrozenInstanceError

import pytest

from rankweave.evaluation import AggregateRankingMetrics
from rankweave.tuning import (
    WeightedRRFTuningReport,
    WeightedRRFTuningTrial,
    tune_weighted_reciprocal_rank_fusion,
)


def _rankings():
    return {
        "query-a": {
            "lexical": ["a", "b"],
            "dense": ["b", "a"],
        },
        "query-b": {
            "lexical": ["c", "d"],
            "dense": ["d", "c"],
        },
    }


def _judgments():
    return {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    }


def test_tuning_selects_best_weight_policy_by_mean_ndcg():
    report = tune_weighted_reciprocal_rank_fusion(
        _rankings(),
        _judgments(),
        {
            "dense-heavy": {"lexical": 0.1, "dense": 0.9},
            "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
        },
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


def test_tuning_supports_reciprocal_rank_objective():
    report = tune_weighted_reciprocal_rank_fusion(
        _rankings(),
        _judgments(),
        {
            "dense-heavy": {"lexical": 0.1, "dense": 0.9},
            "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
        },
        cutoff=1,
        objective_name="mean_reciprocal_rank_at_k",
    )

    assert report.objective_name == "mean_reciprocal_rank_at_k"
    assert report.best_policy_id == "lexical-heavy"


def test_tuning_uses_first_policy_as_deterministic_tie_breaker():
    report = tune_weighted_reciprocal_rank_fusion(
        _rankings(),
        _judgments(),
        {
            "first": {"lexical": 0.5, "dense": 0.5},
            "second": {"lexical": 0.5, "dense": 0.5},
        },
        cutoff=2,
    )

    assert report.best_policy_id == "first"
    assert report.trials[0].objective_score == report.trials[1].objective_score


def test_tuning_rejects_unsupported_objective():
    with pytest.raises(ValueError, match="objective_name must be one of"):
        tune_weighted_reciprocal_rank_fusion(
            _rankings(),
            _judgments(),
            {"policy": {"lexical": 0.5, "dense": 0.5}},
            cutoff=1,
            objective_name="mean_map_at_k",
        )


def test_tuning_rejects_empty_candidate_policy_set():
    with pytest.raises(ValueError, match="at least one candidate"):
        tune_weighted_reciprocal_rank_fusion(
            _rankings(),
            _judgments(),
            {},
            cutoff=1,
        )


def test_tuning_rejects_query_set_mismatch():
    with pytest.raises(ValueError, match="query sets must match"):
        tune_weighted_reciprocal_rank_fusion(
            {"ranked-only": {"dense": ["a"]}},
            {"judged-only": {"a": 1}},
            {"policy": {"dense": 1.0}},
            cutoff=1,
        )


def test_tuning_rejects_empty_query_set():
    with pytest.raises(ValueError, match="at least one query"):
        tune_weighted_reciprocal_rank_fusion(
            {},
            {},
            {"policy": {"dense": 1.0}},
            cutoff=1,
        )


def test_tuning_propagates_invalid_weight_policy():
    with pytest.raises(ValueError, match="sum to 1"):
        tune_weighted_reciprocal_rank_fusion(
            _rankings(),
            _judgments(),
            {"invalid": {"lexical": 0.5, "dense": 0.4}},
            cutoff=1,
        )


@pytest.mark.parametrize("invalid_cutoff", [0, 1.5, True])
def test_tuning_rejects_invalid_cutoff(invalid_cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        tune_weighted_reciprocal_rank_fusion(
            _rankings(),
            _judgments(),
            {"policy": {"lexical": 0.5, "dense": 0.5}},
            cutoff=invalid_cutoff,
        )


@pytest.mark.parametrize("invalid_eta", [0, 1.5, True])
def test_tuning_rejects_invalid_rank_constant(invalid_eta):
    with pytest.raises(ValueError, match="rank_constant_eta"):
        tune_weighted_reciprocal_rank_fusion(
            _rankings(),
            _judgments(),
            {"policy": {"lexical": 0.5, "dense": 0.5}},
            cutoff=1,
            rank_constant_eta=invalid_eta,
        )


def test_tuning_records_are_immutable():
    report = tune_weighted_reciprocal_rank_fusion(
        _rankings(),
        _judgments(),
        {"policy": {"lexical": 0.5, "dense": 0.5}},
        cutoff=1,
    )
    trial = report.trials[0]

    assert isinstance(trial, WeightedRRFTuningTrial)
    assert isinstance(report, WeightedRRFTuningReport)
    with pytest.raises(FrozenInstanceError):
        trial.objective_score = 0.0
    with pytest.raises(FrozenInstanceError):
        report.best_policy_id = "other"
