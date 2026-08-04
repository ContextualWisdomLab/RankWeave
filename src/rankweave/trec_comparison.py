"""Direct paired comparison of standard TREC run and qrels artifacts."""

from dataclasses import dataclass

from rankweave.comparison import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_RANDOMIZATION_COUNT,
    NDCG_AT_K_METRIC,
    TWO_SIDED_ALTERNATIVE,
    RankingComparisonReport,
    compare_rankings,
)
from rankweave.trec import (
    TrecQrels,
    TrecRun,
    parse_trec_qrels,
    parse_trec_run,
)


@dataclass(frozen=True)
class TrecRunComparisonReport:
    """Parsed TREC artifacts and their immutable paired ranking comparison."""

    baseline_run: TrecRun
    candidate_run: TrecRun
    qrels: TrecQrels
    comparison: RankingComparisonReport[str]


def compare_trec_runs(
    baseline_run_text: str,
    candidate_run_text: str,
    qrels_text: str,
    *,
    cutoff: int,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> TrecRunComparisonReport:
    """Parse, evaluate, and statistically compare two standard TREC runs.

    Both runs are converted to decreasing-score rankings and evaluated against
    the same parsed qrels artifact. Existing parser, query-set, metric,
    alternative, cutoff, draw-count, and seed validation errors propagate
    unchanged so malformed benchmark inputs fail at their authoritative layer.
    """
    baseline_run = parse_trec_run(baseline_run_text)
    candidate_run = parse_trec_run(candidate_run_text)
    qrels = parse_trec_qrels(qrels_text)
    comparison = compare_rankings(
        baseline_run.rankings_by_query(),
        candidate_run.rankings_by_query(),
        qrels.relevance_by_query(),
        cutoff=cutoff,
        metric_name=metric_name,
        alternative=alternative,
        randomization_count=randomization_count,
        random_seed=random_seed,
    )
    return TrecRunComparisonReport(
        baseline_run=baseline_run,
        candidate_run=candidate_run,
        qrels=qrels,
        comparison=comparison,
    )
