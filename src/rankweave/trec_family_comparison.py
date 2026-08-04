"""Family-wise comparison of one baseline and named TREC candidate runs."""

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from rankweave._validation import _require_unit_interval
from rankweave.comparison import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_RANDOMIZATION_COUNT,
    NDCG_AT_K_METRIC,
    TWO_SIDED_ALTERNATIVE,
    RankingComparisonReport,
    compare_ranking_reports,
)
from rankweave.evaluation import evaluate_rankings
from rankweave.trec import TrecQrels, TrecRun, parse_trec_qrels, parse_trec_run

CandidateIdentifier = TypeVar("CandidateIdentifier", bound=Hashable)


@dataclass(frozen=True)
class TrecCandidateComparison(Generic[CandidateIdentifier]):
    """One named candidate artifact, comparison, and Holm decision evidence."""

    candidate_id: CandidateIdentifier
    candidate_run: TrecRun
    comparison: RankingComparisonReport[str]
    raw_p_value: float
    holm_adjusted_p_value: float
    rejected_at_familywise_alpha: bool


@dataclass(frozen=True)
class TrecRunFamilyComparisonReport(Generic[CandidateIdentifier]):
    """One baseline, shared qrels, and an ordered family of candidate results."""

    baseline_run: TrecRun
    qrels: TrecQrels
    metric_name: str
    alternative: str
    familywise_alpha: float
    candidates: tuple[TrecCandidateComparison[CandidateIdentifier], ...]


def _require_familywise_alpha(value: float) -> float:
    """Return a finite family-wise alpha in the half-open unit interval."""
    _require_unit_interval(value, "familywise_alpha")
    if value == 0.0:
        raise ValueError("familywise_alpha must be greater than 0")
    return float(value)


def _snapshot_candidates(
    candidate_run_texts: Mapping[CandidateIdentifier, str],
) -> tuple[tuple[CandidateIdentifier, str], ...]:
    """Snapshot a non-empty candidate mapping with unique hashable identifiers."""
    if not isinstance(candidate_run_texts, Mapping):
        raise ValueError("candidate_run_texts must be a mapping")
    candidate_items = tuple(candidate_run_texts.items())
    if not candidate_items:
        raise ValueError("candidate_run_texts must contain at least one candidate")

    seen_candidate_ids: set[CandidateIdentifier] = set()
    for candidate_id, _ in candidate_items:
        try:
            if candidate_id in seen_candidate_ids:
                raise ValueError(f"duplicate candidate identifier {candidate_id!r}")
            seen_candidate_ids.add(candidate_id)
        except TypeError as exc:
            raise ValueError("candidate identifiers must be hashable") from exc
    return candidate_items


def _holm_adjusted_p_values(raw_p_values: tuple[float, ...]) -> tuple[float, ...]:
    """Return monotone Holm-adjusted p-values in original candidate order."""
    family_size = len(raw_p_values)
    ordered_indices = sorted(
        range(family_size),
        key=lambda index: (raw_p_values[index], index),
    )
    adjusted_values = [0.0] * family_size
    cumulative_maximum = 0.0
    for sorted_position, original_index in enumerate(ordered_indices):
        scaled_value = min(
            1.0,
            (family_size - sorted_position) * raw_p_values[original_index],
        )
        cumulative_maximum = max(cumulative_maximum, scaled_value)
        adjusted_values[original_index] = cumulative_maximum
    return tuple(adjusted_values)


def compare_trec_run_family(
    baseline_run_text: str,
    candidate_run_texts: Mapping[CandidateIdentifier, str],
    qrels_text: str,
    *,
    cutoff: int,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    familywise_alpha: float = 0.05,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> TrecRunFamilyComparisonReport[CandidateIdentifier]:
    """Compare a baseline with named TREC candidates using Holm correction.

    Baseline and qrels artifacts are parsed and evaluated once. Candidate order
    follows mapping insertion order. Each candidate receives the same explicit
    randomization seed, creating reproducible common sign streams without
    touching global random state. Candidate-specific failures retain the
    candidate identifier while preserving the lower-level error message.
    """
    validated_alpha = _require_familywise_alpha(familywise_alpha)
    candidate_items = _snapshot_candidates(candidate_run_texts)
    baseline_run = parse_trec_run(baseline_run_text)
    qrels = parse_trec_qrels(qrels_text)
    relevance_by_query = qrels.relevance_by_query()
    baseline_report = evaluate_rankings(
        baseline_run.rankings_by_query(),
        relevance_by_query,
        cutoff=cutoff,
    )

    unadjusted_candidates: list[
        tuple[CandidateIdentifier, TrecRun, RankingComparisonReport[str]]
    ] = []
    for candidate_id, candidate_run_text in candidate_items:
        try:
            candidate_run = parse_trec_run(candidate_run_text)
            candidate_report = evaluate_rankings(
                candidate_run.rankings_by_query(),
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
        except ValueError as exc:
            raise ValueError(f"candidate {candidate_id!r}: {exc}") from exc
        unadjusted_candidates.append(
            (
                candidate_id,
                candidate_run,
                RankingComparisonReport(
                    baseline=baseline_report,
                    candidate=candidate_report,
                    significance=significance,
                ),
            )
        )

    raw_p_values = tuple(
        comparison.significance.p_value
        for _, _, comparison in unadjusted_candidates
    )
    adjusted_p_values = _holm_adjusted_p_values(raw_p_values)
    candidates = tuple(
        TrecCandidateComparison(
            candidate_id=candidate_id,
            candidate_run=candidate_run,
            comparison=comparison,
            raw_p_value=comparison.significance.p_value,
            holm_adjusted_p_value=adjusted_p_value,
            rejected_at_familywise_alpha=adjusted_p_value <= validated_alpha,
        )
        for (
            candidate_id,
            candidate_run,
            comparison,
        ), adjusted_p_value in zip(
            unadjusted_candidates,
            adjusted_p_values,
            strict=True,
        )
    )
    first_significance = candidates[0].comparison.significance
    return TrecRunFamilyComparisonReport(
        baseline_run=baseline_run,
        qrels=qrels,
        metric_name=first_significance.metric_name,
        alternative=first_significance.alternative,
        familywise_alpha=validated_alpha,
        candidates=candidates,
    )
