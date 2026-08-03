import pytest

from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    MEAN_PRECISION_OBJECTIVE,
    MEAN_RECALL_OBJECTIVE,
    MEAN_RECIPROCAL_RANK_OBJECTIVE,
    tune_weighted_reciprocal_rank_fusion,
)


@pytest.mark.parametrize(
    "objective_name",
    [
        MEAN_NDCG_OBJECTIVE,
        MEAN_RECIPROCAL_RANK_OBJECTIVE,
        MEAN_RECALL_OBJECTIVE,
        MEAN_PRECISION_OBJECTIVE,
    ],
)
def test_tuning_accepts_every_supported_objective(objective_name):
    report = tune_weighted_reciprocal_rank_fusion(
        {
            "query": {
                "lexical": ["relevant", "other"],
                "dense": ["other", "relevant"],
            }
        },
        {"query": {"relevant": 1}},
        {"policy": {"lexical": 0.9, "dense": 0.1}},
        cutoff=1,
        objective_name=objective_name,
    )

    assert report.objective_name == objective_name
    assert report.best_policy_id == "policy"


def test_tuning_rejects_policy_missing_a_result_channel_weight():
    with pytest.raises(ValueError, match="without weights"):
        tune_weighted_reciprocal_rank_fusion(
            {
                "query": {
                    "lexical": ["relevant"],
                    "dense": ["other"],
                }
            },
            {"query": {"relevant": 1}},
            {"invalid": {"dense": 1.0}},
            cutoff=1,
        )
