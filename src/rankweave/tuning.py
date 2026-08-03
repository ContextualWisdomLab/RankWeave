"""Deterministic offline tuning for weighted rank-fusion policies."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.evaluation import RankingEvaluationReport, evaluate_rankings
from rankweave.ranked_list_fusion import weighted_reciprocal_rank_fuse

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
PolicyIdentifier = TypeVar("PolicyIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)

MEAN_NDCG_OBJECTIVE = "mean_ndcg_at_k"
MEAN_RECIPROCAL_RANK_OBJECTIVE = "mean_reciprocal_rank_at_k"
MEAN_RECALL_OBJECTIVE = "mean_recall_at_k"
MEAN_PRECISION_OBJECTIVE = "mean_precision_at_k"

SUPPORTED_TUNING_OBJECTIVES = frozenset(
    {
        MEAN_NDCG_OBJECTIVE,
        MEAN_RECIPROCAL_RANK_OBJECTIVE,
        MEAN_RECALL_OBJECTIVE,
        MEAN_PRECISION_OBJECTIVE,
    }
)


@dataclass(frozen=True)
class WeightedRRFTuningTrial(Generic[PolicyIdentifier, QueryIdentifier]):
    """One candidate weight policy and its immutable evaluation evidence."""

    policy_id: PolicyIdentifier
    channel_weights: tuple[tuple[str, float], ...]
    objective_score: float
    evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedRRFTuningReport(Generic[PolicyIdentifier, QueryIdentifier]):
    """All tuning trials plus the deterministic best weighted-RRF policy."""

    cutoff: int
    rank_constant_eta: int
    objective_name: str
    trials: tuple[
        WeightedRRFTuningTrial[PolicyIdentifier, QueryIdentifier], ...
    ]
    best_policy_id: PolicyIdentifier
    best_channel_weights: tuple[tuple[str, float], ...]
    best_objective_score: float


def tune_weighted_reciprocal_rank_fusion(
    channel_rankings_by_query: Mapping[
        QueryIdentifier, Mapping[str, Sequence[ItemIdentifier]]
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    *,
    cutoff: int,
    rank_constant_eta: int = 60,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedRRFTuningReport[PolicyIdentifier, QueryIdentifier]:
    """Select a fixed weighted-RRF policy on a judged validation query set.

    Each candidate maps a caller-defined policy identifier to convex channel
    weights. For every policy, RankWeave fuses every query, evaluates the
    resulting rankings, and records the full immutable report. The first
    candidate wins exact objective ties, making selection deterministic.

    This function performs offline validation-set selection. Callers should
    report final effectiveness on a separate held-out test set to avoid
    optimistic estimates from tuning and evaluating on the same judgments.
    """
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    if objective_name not in SUPPORTED_TUNING_OBJECTIVES:
        raise ValueError(
            "objective_name must be one of "
            f"{sorted(SUPPORTED_TUNING_OBJECTIVES)!r}"
        )
    if not candidate_channel_weights:
        raise ValueError("tuning requires at least one candidate policy")

    # Validate the query universe and judgments before evaluating policies.
    evaluate_rankings(
        {query_id: () for query_id in channel_rankings_by_query},
        relevance_by_query,
        cutoff=validated_cutoff,
    )

    trials = []
    for policy_id, channel_weights in candidate_channel_weights.items():
        fused_rankings_by_query = {
            query_id: tuple(
                fused_item.item_id
                for fused_item in weighted_reciprocal_rank_fuse(
                    channel_rankings,
                    channel_weights,
                    rank_constant_eta=validated_eta,
                    limit=validated_cutoff,
                )
            )
            for query_id, channel_rankings in channel_rankings_by_query.items()
        }
        evaluation = evaluate_rankings(
            fused_rankings_by_query,
            relevance_by_query,
            cutoff=validated_cutoff,
        )
        objective_score = getattr(evaluation.aggregate, objective_name)
        trials.append(
            WeightedRRFTuningTrial(
                policy_id=policy_id,
                channel_weights=tuple(channel_weights.items()),
                objective_score=objective_score,
                evaluation=evaluation,
            )
        )

    best_trial = trials[0]
    for trial in trials[1:]:
        if trial.objective_score > best_trial.objective_score:
            best_trial = trial

    return WeightedRRFTuningReport(
        cutoff=validated_cutoff,
        rank_constant_eta=validated_eta,
        objective_name=objective_name,
        trials=tuple(trials),
        best_policy_id=best_trial.policy_id,
        best_channel_weights=best_trial.channel_weights,
        best_objective_score=best_trial.objective_score,
    )
