"""Explicit-fold cross-validation for fixed convex score-fusion policies."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.evaluation import RankingEvaluationReport, evaluate_rankings
from rankweave.ranked_list_fusion import weighted_convex_fuse
from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    SUPPORTED_TUNING_OBJECTIVES,
    WeightedConvexTuningReport,
    tune_weighted_convex_fusion,
)

FoldIdentifier = TypeVar("FoldIdentifier", bound=Hashable)
ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
PolicyIdentifier = TypeVar("PolicyIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)


@dataclass(frozen=True)
class WeightedConvexCrossValidationFold(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    """One training-selected policy and its held-out fold evaluation."""

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
    """Explicit folds, out-of-fold evidence, and final full-data tuning."""

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
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    if objective_name not in SUPPORTED_TUNING_OBJECTIVES:
        raise ValueError(
            "objective_name must be one of "
            f"{sorted(SUPPORTED_TUNING_OBJECTIVES)!r}"
        )
    if not candidate_channel_weights:
        raise ValueError("tuning requires at least one candidate policy")

    query_ids = tuple(channel_results_by_query)
    # Reuse the established query-universe and judgment validation boundary.
    evaluate_rankings(
        {query_id: () for query_id in query_ids},
        relevance_by_query,
        cutoff=validated_cutoff,
    )

    scored_query_ids = set(query_ids)
    fold_query_ids = set(fold_id_by_query)
    if fold_query_ids != scored_query_ids:
        missing_assignments = sorted(
            scored_query_ids - fold_query_ids, key=repr
        )
        extra_assignments = sorted(
            fold_query_ids - scored_query_ids, key=repr
        )
        raise ValueError(
            "fold assignments must match scored queries; "
            f"missing assignments={missing_assignments!r}, "
            f"extra assignments={extra_assignments!r}"
        )

    fold_ids = _ordered_fold_ids(query_ids, fold_id_by_query)
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
