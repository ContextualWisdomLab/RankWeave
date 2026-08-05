"""Explicit-fold cross-validation for fixed retrieval-fusion policies."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.evaluation import RankingEvaluationReport, evaluate_rankings
from rankweave.ranked_list_fusion import (
    weighted_convex_fuse,
    weighted_reciprocal_rank_fuse,
)
from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    SUPPORTED_TUNING_OBJECTIVES,
    WeightedConvexTuningReport,
    WeightedRRFTuningReport,
    tune_weighted_convex_fusion,
    tune_weighted_reciprocal_rank_fusion,
)

FoldIdentifier = TypeVar("FoldIdentifier", bound=Hashable)
ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
PolicyIdentifier = TypeVar("PolicyIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)


@dataclass(frozen=True)
class WeightedConvexCrossValidationFold(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    """One training-selected convex policy and held-out fold evaluation."""

    fold_id: FoldIdentifier
    training_query_ids: tuple[QueryIdentifier, ...]
    held_out_query_ids: tuple[QueryIdentifier, ...]
    tuning: WeightedConvexTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]
    held_out_evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedConvexCrossValidationReport(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    """Convex folds, out-of-fold evidence, and final full-data tuning."""

    cutoff: int
    objective_name: str
    folds: tuple[
        WeightedConvexCrossValidationFold[
            FoldIdentifier, PolicyIdentifier, QueryIdentifier
        ], ...
    ]
    out_of_fold_evaluation: RankingEvaluationReport[QueryIdentifier]
    final_tuning: WeightedConvexTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]


@dataclass(frozen=True)
class WeightedRRFCrossValidationFold(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    """One training-selected weighted-RRF policy and held-out evaluation."""

    fold_id: FoldIdentifier
    training_query_ids: tuple[QueryIdentifier, ...]
    held_out_query_ids: tuple[QueryIdentifier, ...]
    tuning: WeightedRRFTuningReport[PolicyIdentifier, QueryIdentifier]
    held_out_evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedRRFCrossValidationReport(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    """Weighted-RRF folds, out-of-fold evidence, and final tuning."""

    cutoff: int
    rank_constant_eta: int
    objective_name: str
    folds: tuple[
        WeightedRRFCrossValidationFold[
            FoldIdentifier, PolicyIdentifier, QueryIdentifier
        ], ...
    ]
    out_of_fold_evaluation: RankingEvaluationReport[QueryIdentifier]
    final_tuning: WeightedRRFTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]


def _ordered_fold_ids(
    query_ids: tuple[QueryIdentifier, ...],
    fold_id_by_query: Mapping[QueryIdentifier, FoldIdentifier],
) -> tuple[FoldIdentifier, ...]:
    """Return distinct fold identifiers in first-query appearance order."""
    ordered_fold_ids: list[FoldIdentifier] = []
    seen_fold_ids: set[FoldIdentifier] = set()
    for query_id in query_ids:
        fold_id = fold_id_by_query[query_id]
        try:
            if fold_id not in seen_fold_ids:
                seen_fold_ids.add(fold_id)
                ordered_fold_ids.append(fold_id)
        except TypeError as exc:
            raise ValueError(
                f"fold identifier for query {query_id!r} must be hashable"
            ) from exc
    if len(ordered_fold_ids) < 2:
        raise ValueError(
            "cross-validation requires at least two distinct folds"
        )
    return tuple(ordered_fold_ids)


def _validate_cross_validation_request(
    query_values_by_query: Mapping[QueryIdentifier, object],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    fold_id_by_query: Mapping[QueryIdentifier, FoldIdentifier],
    *,
    cutoff: int,
    objective_name: str,
    query_kind: str,
) -> tuple[
    int,
    tuple[QueryIdentifier, ...],
    tuple[FoldIdentifier, ...],
]:
    """Validate shared objective, query-universe, and fold contracts."""
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    if objective_name not in SUPPORTED_TUNING_OBJECTIVES:
        raise ValueError(
            "objective_name must be one of "
            f"{sorted(SUPPORTED_TUNING_OBJECTIVES)!r}"
        )
    if not candidate_channel_weights:
        raise ValueError("tuning requires at least one candidate policy")

    query_ids = tuple(query_values_by_query)
    evaluate_rankings(
        {query_id: () for query_id in query_ids},
        relevance_by_query,
        cutoff=validated_cutoff,
    )

    query_id_set = set(query_ids)
    fold_query_ids = set(fold_id_by_query)
    if fold_query_ids != query_id_set:
        missing_assignments = sorted(
            query_id_set - fold_query_ids, key=repr
        )
        extra_assignments = sorted(
            fold_query_ids - query_id_set, key=repr
        )
        raise ValueError(
            f"fold assignments must match {query_kind} queries; "
            f"missing assignments={missing_assignments!r}, "
            f"extra assignments={extra_assignments!r}"
        )

    fold_ids = _ordered_fold_ids(query_ids, fold_id_by_query)
    return validated_cutoff, query_ids, fold_ids


def cross_validate_weighted_convex_fusion(
    channel_results_by_query: Mapping[
        QueryIdentifier,
        Mapping[str, Sequence[tuple[ItemIdentifier, float]]],
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    fold_id_by_query: Mapping[QueryIdentifier, FoldIdentifier],
    *,
    cutoff: int,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedConvexCrossValidationReport[
    FoldIdentifier, PolicyIdentifier, QueryIdentifier
]:
    """Evaluate a convex-policy selection procedure on explicit held-out folds.

    The caller owns fold construction. Every fold selects one fixed policy only
    from the complementary training queries, applies it unchanged to the
    held-out queries, and retains the complete training and held-out evidence.
    The aggregate out-of-fold report estimates the observed selection procedure
    under the supplied fold design. ``final_tuning`` separately recommends one
    policy using all judgments and is not a held-out performance estimate.

    Use grouped or blocked fold identifiers whenever paraphrases, translations,
    revisions, users, tenants, events, projects, or time windows must not cross
    the training/held-out boundary. This function does not generate random
    folds or claim that a caller-supplied split is leakage-safe.
    """
    validated_cutoff, query_ids, fold_ids = (
        _validate_cross_validation_request(
            channel_results_by_query,
            relevance_by_query,
            candidate_channel_weights,
            fold_id_by_query,
            cutoff=cutoff,
            objective_name=objective_name,
            query_kind="scored",
        )
    )
    fold_reports = []
    out_of_fold_rankings: dict[
        QueryIdentifier, tuple[ItemIdentifier, ...]
    ] = {}

    for fold_id in fold_ids:
        held_out_query_ids = tuple(
            query_id
            for query_id in query_ids
            if fold_id_by_query[query_id] == fold_id
        )
        training_query_ids = tuple(
            query_id
            for query_id in query_ids
            if fold_id_by_query[query_id] != fold_id
        )
        training_results = {
            query_id: channel_results_by_query[query_id]
            for query_id in training_query_ids
        }
        training_relevance = {
            query_id: relevance_by_query[query_id]
            for query_id in training_query_ids
        }
        tuning = tune_weighted_convex_fusion(
            training_results,
            training_relevance,
            candidate_channel_weights,
            cutoff=validated_cutoff,
            objective_name=objective_name,
        )
        selected_weights = dict(tuning.best_channel_weights)
        held_out_rankings = {
            query_id: tuple(
                fused_item.item_id
                for fused_item in weighted_convex_fuse(
                    channel_results_by_query[query_id],
                    selected_weights,
                    limit=validated_cutoff,
                )
            )
            for query_id in held_out_query_ids
        }
        held_out_evaluation = evaluate_rankings(
            held_out_rankings,
            {
                query_id: relevance_by_query[query_id]
                for query_id in held_out_query_ids
            },
            cutoff=validated_cutoff,
        )
        out_of_fold_rankings.update(held_out_rankings)
        fold_reports.append(
            WeightedConvexCrossValidationFold(
                fold_id=fold_id,
                training_query_ids=training_query_ids,
                held_out_query_ids=held_out_query_ids,
                tuning=tuning,
                held_out_evaluation=held_out_evaluation,
            )
        )

    ordered_out_of_fold_rankings = {
        query_id: out_of_fold_rankings[query_id] for query_id in query_ids
    }
    out_of_fold_evaluation = evaluate_rankings(
        ordered_out_of_fold_rankings,
        relevance_by_query,
        cutoff=validated_cutoff,
    )
    final_tuning = tune_weighted_convex_fusion(
        channel_results_by_query,
        relevance_by_query,
        candidate_channel_weights,
        cutoff=validated_cutoff,
        objective_name=objective_name,
    )
    return WeightedConvexCrossValidationReport(
        cutoff=validated_cutoff,
        objective_name=objective_name,
        folds=tuple(fold_reports),
        out_of_fold_evaluation=out_of_fold_evaluation,
        final_tuning=final_tuning,
    )


def cross_validate_weighted_reciprocal_rank_fusion(
    channel_rankings_by_query: Mapping[
        QueryIdentifier, Mapping[str, Sequence[ItemIdentifier]]
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    fold_id_by_query: Mapping[QueryIdentifier, FoldIdentifier],
    *,
    cutoff: int,
    rank_constant_eta: int = 60,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedRRFCrossValidationReport[
    FoldIdentifier, PolicyIdentifier, QueryIdentifier
]:
    """Evaluate fixed weighted-RRF selection on explicit held-out folds.

    Every fold selects channel weights only from its complementary training
    queries, applies the chosen policy unchanged to the held-out rank lists,
    and uses one fixed ``rank_constant_eta`` for training, assessment, and final
    tuning. The aggregate out-of-fold report estimates the supplied selection
    procedure. ``final_tuning`` uses all judgments and is not held-out evidence.

    The caller owns leakage-safe fold construction. Keep paraphrases,
    translations, revisions, users, tenants, events, projects, or time blocks
    together whenever their dependence must not cross the assessment boundary.
    """
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    validated_cutoff, query_ids, fold_ids = (
        _validate_cross_validation_request(
            channel_rankings_by_query,
            relevance_by_query,
            candidate_channel_weights,
            fold_id_by_query,
            cutoff=cutoff,
            objective_name=objective_name,
            query_kind="ranked",
        )
    )
    fold_reports = []
    out_of_fold_rankings: dict[
        QueryIdentifier, tuple[ItemIdentifier, ...]
    ] = {}

    for fold_id in fold_ids:
        held_out_query_ids = tuple(
            query_id
            for query_id in query_ids
            if fold_id_by_query[query_id] == fold_id
        )
        training_query_ids = tuple(
            query_id
            for query_id in query_ids
            if fold_id_by_query[query_id] != fold_id
        )
        training_rankings = {
            query_id: channel_rankings_by_query[query_id]
            for query_id in training_query_ids
        }
        training_relevance = {
            query_id: relevance_by_query[query_id]
            for query_id in training_query_ids
        }
        tuning = tune_weighted_reciprocal_rank_fusion(
            training_rankings,
            training_relevance,
            candidate_channel_weights,
            cutoff=validated_cutoff,
            rank_constant_eta=validated_eta,
            objective_name=objective_name,
        )
        selected_weights = dict(tuning.best_channel_weights)
        held_out_rankings = {
            query_id: tuple(
                fused_item.item_id
                for fused_item in weighted_reciprocal_rank_fuse(
                    channel_rankings_by_query[query_id],
                    selected_weights,
                    rank_constant_eta=validated_eta,
                    limit=validated_cutoff,
                )
            )
            for query_id in held_out_query_ids
        }
        held_out_evaluation = evaluate_rankings(
            held_out_rankings,
            {
                query_id: relevance_by_query[query_id]
                for query_id in held_out_query_ids
            },
            cutoff=validated_cutoff,
        )
        out_of_fold_rankings.update(held_out_rankings)
        fold_reports.append(
            WeightedRRFCrossValidationFold(
                fold_id=fold_id,
                training_query_ids=training_query_ids,
                held_out_query_ids=held_out_query_ids,
                tuning=tuning,
                held_out_evaluation=held_out_evaluation,
            )
        )

    ordered_out_of_fold_rankings = {
        query_id: out_of_fold_rankings[query_id] for query_id in query_ids
    }
    out_of_fold_evaluation = evaluate_rankings(
        ordered_out_of_fold_rankings,
        relevance_by_query,
        cutoff=validated_cutoff,
    )
    final_tuning = tune_weighted_reciprocal_rank_fusion(
        channel_rankings_by_query,
        relevance_by_query,
        candidate_channel_weights,
        cutoff=validated_cutoff,
        rank_constant_eta=validated_eta,
        objective_name=objective_name,
    )
    return WeightedRRFCrossValidationReport(
        cutoff=validated_cutoff,
        rank_constant_eta=validated_eta,
        objective_name=objective_name,
        folds=tuple(fold_reports),
        out_of_fold_evaluation=out_of_fold_evaluation,
        final_tuning=final_tuning,
    )
