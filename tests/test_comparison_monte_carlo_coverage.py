from rankweave.comparison import (
    MONTE_CARLO_RANDOMIZATION_METHOD,
    compare_ranking_reports,
)
from rankweave.evaluation import (
    AggregateRankingMetrics,
    QueryRankingMetrics,
    RankingEvaluationReport,
    RankingMetrics,
)


def _report(values):
    query_metrics = tuple(
        QueryRankingMetrics(
            f"query-{index}",
            RankingMetrics(1, 1, 0, 0, value, value, value, value),
        )
        for index, value in enumerate(values)
    )
    mean_value = sum(values) / len(values)
    return RankingEvaluationReport(
        1,
        query_metrics,
        AggregateRankingMetrics(
            len(values),
            mean_value,
            mean_value,
            mean_value,
            mean_value,
        ),
    )


def test_monte_carlo_counts_extreme_and_non_extreme_assignments():
    baseline = _report([0.5] * 17)
    candidate = _report([0.6] * 11 + [0.4] * 6)

    result = compare_ranking_reports(
        baseline,
        candidate,
        randomization_count=1_000,
        random_seed=11,
    )

    assert result.method == MONTE_CARLO_RANDOMIZATION_METHOD
    assert 1.0 / 1_001 < result.p_value < 1.0
