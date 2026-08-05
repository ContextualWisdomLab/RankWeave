from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    WeightedRRFCrossValidationFold,
    WeightedRRFCrossValidationReport,
    cross_validate_weighted_reciprocal_rank_fusion,
)
from rankweave.tuning import SUPPORTED_TUNING_OBJECTIVES


def _blocked_rankings():
    return {
        "query-a1": {
            "lexical": ["a", "x"],
            "dense": ["x", "a"],
        },
        "query-b1": {
            "lexical": ["y", "b"],
            "dense": ["b", "y"],
        },
        "query-a2": {
            "lexical": ["c", "z"],
            "dense": ["z", "c"],
        },
        "query-b2": {
            "lexical": ["w", "d"],
            "dense": ["d", "w"],
        },
    }


def _blocked_judgments():
    return {
        "query-a1": {"a": 3},
        "query-b1": {"b": 3},
        "query-a2": {"c": 3},
        "query-b2": {"d": 3},
    }


def _fold_assignments():
    return {
        "query-a1": "fold-a",
        "query-b1": "fold-b",
        "query-a2": "fold-a",
        "query-b2": "fold-b",
    }


def _candidate_weights():
    return {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    }


def test_rrf_cross_validation_preserves_blocks_eta_and_oof_order():
    report = cross_validate_weighted_reciprocal_rank_fusion(
        _blocked_rankings(),
        _blocked_judgments(),
        _candidate_weights(),
        _fold_assignments(),
        cutoff=1,
        rank_constant_eta=17,
    )

    assert report.rank_constant_eta == 17
    assert [fold.fold_id for fold in report.folds] == ["fold-a", "fold-b"]
    assert report.folds[0].training_query_ids == ("query-b1", "query-b2")
    assert report.folds[0].held_out_query_ids == ("query-a1", "query-a2")
    assert report.folds[0].tuning.rank_constant_eta == 17
    assert report.folds[0].tuning.best_policy_id == "dense-heavy"
    assert report.folds[0].held_out_evaluation.aggregate.mean_ndcg_at_k == 0.0

    assert report.folds[1].training_query_ids == ("query-a1", "query-a2")
    assert report.folds[1].held_out_query_ids == ("query-b1", "query-b2")
    assert report.folds[1].tuning.rank_constant_eta == 17
    assert report.folds[1].tuning.best_policy_id == "lexical-heavy"
    assert report.folds[1].held_out_evaluation.aggregate.mean_ndcg_at_k == 0.0

    assert [
        entry.query_id
        for entry in report.out_of_fold_evaluation.query_metrics
    ] == ["query-a1", "query-b1", "query-a2", "query-b2"]
    assert report.out_of_fold_evaluation.aggregate.query_count == 4
    assert report.out_of_fold_evaluation.aggregate.mean_ndcg_at_k == 0.0

    assert report.final_tuning.rank_constant_eta == 17
    assert report.final_tuning.best_policy_id == "dense-heavy"
    assert report.final_tuning.best_objective_score == 0.5


@pytest.mark.parametrize("objective_name", sorted(SUPPORTED_TUNING_OBJECTIVES))
def test_rrf_cross_validation_supports_every_tuning_objective(objective_name):
    report = cross_validate_weighted_reciprocal_rank_fusion(
        _blocked_rankings(),
        _blocked_judgments(),
        _candidate_weights(),
        _fold_assignments(),
        cutoff=1,
        objective_name=objective_name,
    )

    assert report.objective_name == objective_name
    assert report.folds[0].tuning.best_policy_id == "dense-heavy"
    assert report.folds[1].tuning.best_policy_id == "lexical-heavy"
    assert report.out_of_fold_evaluation.aggregate.query_count == 4


def test_rrf_cross_validation_uses_first_policy_for_exact_ties():
    report = cross_validate_weighted_reciprocal_rank_fusion(
        _blocked_rankings(),
        _blocked_judgments(),
        {
            "first": {"lexical": 0.5, "dense": 0.5},
            "second": {"lexical": 0.5, "dense": 0.5},
        },
        _fold_assignments(),
        cutoff=2,
    )

    assert all(fold.tuning.best_policy_id == "first" for fold in report.folds)
    assert report.final_tuning.best_policy_id == "first"


def test_rrf_cross_validation_rejects_missing_and_extra_fold_assignments():
    folds = _fold_assignments()
    del folds["query-a2"]
    folds["extra-query"] = "fold-c"

    with pytest.raises(
        ValueError,
        match=(
            r"fold assignments must match ranked queries; "
            r"missing assignments=\['query-a2'\], "
            r"extra assignments=\['extra-query'\]"
        ),
    ):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            folds,
            cutoff=1,
        )


@pytest.mark.parametrize(
    "folds",
    [
        {},
        {
            "query-a1": "only",
            "query-b1": "only",
            "query-a2": "only",
            "query-b2": "only",
        },
    ],
)
def test_rrf_cross_validation_requires_two_distinct_folds(folds):
    if not folds:
        with pytest.raises(ValueError, match="fold assignments must match"):
            cross_validate_weighted_reciprocal_rank_fusion(
                _blocked_rankings(),
                _blocked_judgments(),
                _candidate_weights(),
                folds,
                cutoff=1,
            )
        return

    with pytest.raises(ValueError, match="at least two distinct folds"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            folds,
            cutoff=1,
        )


def test_rrf_cross_validation_rejects_unhashable_fold_identifier():
    folds = _fold_assignments()
    folds["query-a1"] = ["unhashable"]

    with pytest.raises(ValueError, match="fold identifier.*must be hashable"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            folds,
            cutoff=1,
        )


@pytest.mark.parametrize("invalid_cutoff", [0, 1.5, True])
def test_rrf_cross_validation_rejects_invalid_cutoff(invalid_cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=invalid_cutoff,
        )


@pytest.mark.parametrize("invalid_eta", [0, 1.5, True])
def test_rrf_cross_validation_rejects_invalid_rank_constant(invalid_eta):
    with pytest.raises(ValueError, match="rank_constant_eta"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=1,
            rank_constant_eta=invalid_eta,
        )


def test_rrf_cross_validation_rejects_unsupported_objective():
    with pytest.raises(ValueError, match="objective_name must be one of"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=1,
            objective_name="mean_map_at_k",
        )


def test_rrf_cross_validation_rejects_empty_policy_family():
    with pytest.raises(ValueError, match="at least one candidate"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            {},
            _fold_assignments(),
            cutoff=1,
        )


def test_rrf_cross_validation_propagates_non_convex_weights():
    with pytest.raises(ValueError, match="sum to 1"):
        cross_validate_weighted_reciprocal_rank_fusion(
            _blocked_rankings(),
            _blocked_judgments(),
            {"invalid": {"lexical": 0.4, "dense": 0.4}},
            _fold_assignments(),
            cutoff=1,
        )


def test_rrf_cross_validation_propagates_duplicate_item_error():
    rankings = _blocked_rankings()
    rankings["query-a1"]["lexical"] = ["a", "a"]

    with pytest.raises(ValueError, match="contains duplicate item"):
        cross_validate_weighted_reciprocal_rank_fusion(
            rankings,
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=1,
        )


def test_rrf_cross_validation_propagates_unhashable_item_error():
    rankings = _blocked_rankings()
    rankings["query-a1"]["lexical"] = [["unhashable"]]

    with pytest.raises(ValueError, match="must be hashable"):
        cross_validate_weighted_reciprocal_rank_fusion(
            rankings,
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=1,
        )


def test_rrf_cross_validation_rejects_result_channel_without_weight():
    rankings = _blocked_rankings()
    rankings["query-a1"]["graph"] = ["a"]

    with pytest.raises(ValueError, match="channels without weights"):
        cross_validate_weighted_reciprocal_rank_fusion(
            rankings,
            _blocked_judgments(),
            _candidate_weights(),
            _fold_assignments(),
            cutoff=1,
        )


def test_rrf_cross_validation_records_are_immutable_and_exported():
    report = cross_validate_weighted_reciprocal_rank_fusion(
        _blocked_rankings(),
        _blocked_judgments(),
        _candidate_weights(),
        _fold_assignments(),
        cutoff=1,
    )
    fold = report.folds[0]

    assert isinstance(fold, WeightedRRFCrossValidationFold)
    assert isinstance(report, WeightedRRFCrossValidationReport)
    with pytest.raises(FrozenInstanceError):
        fold.fold_id = "other"
    with pytest.raises(FrozenInstanceError):
        report.rank_constant_eta = 10
