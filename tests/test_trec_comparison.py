from dataclasses import FrozenInstanceError

import pytest

from rankweave.comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    MONTE_CARLO_RANDOMIZATION_METHOD,
    PRECISION_AT_K_METRIC,
)
from rankweave.trec import TrecQrels, TrecRun
from rankweave.trec_comparison import (
    TrecRunComparisonReport,
    compare_trec_runs,
)

QRELS_TEXT = """
# judged topics
query-a 0 relevant-a 1
query-a 0 irrelevant-a 0
query-b 0 relevant-b 1
query-b 0 irrelevant-b 0
"""

BASELINE_RUN_TEXT = """
# baseline scores put nonrelevant documents first
query-a Q0 irrelevant-a 2 0.9 baseline.run
query-a Q0 relevant-a 1 0.4 baseline.run
query-b Q0 irrelevant-b 2 0.8 baseline.run
query-b Q0 relevant-b 1 0.3 baseline.run
"""

CANDIDATE_RUN_TEXT = """
# candidate scores put relevant documents first
query-a Q0 irrelevant-a 1 0.2 candidate_run
query-a Q0 relevant-a 2 0.9 candidate_run
query-b Q0 irrelevant-b 1 0.1 candidate_run
query-b Q0 relevant-b 2 0.8 candidate_run
"""


def test_compare_trec_runs_preserves_artifacts_and_computes_exact_lift():
    report = compare_trec_runs(
        BASELINE_RUN_TEXT,
        CANDIDATE_RUN_TEXT,
        QRELS_TEXT,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
    )

    assert isinstance(report, TrecRunComparisonReport)
    assert isinstance(report.baseline_run, TrecRun)
    assert isinstance(report.candidate_run, TrecRun)
    assert isinstance(report.qrels, TrecQrels)
    assert report.baseline_run.run_id == "baseline.run"
    assert report.candidate_run.run_id == "candidate_run"
    assert report.baseline_run.rankings_by_query()["query-a"][0] == "irrelevant-a"
    assert report.candidate_run.rankings_by_query()["query-a"][0] == "relevant-a"
    assert report.comparison.baseline.aggregate.mean_ndcg_at_k == 0.0
    assert report.comparison.candidate.aggregate.mean_ndcg_at_k == 1.0
    assert report.comparison.significance.mean_difference == 1.0
    assert report.comparison.significance.p_value == pytest.approx(0.25)
    assert report.comparison.significance.query_count == 2


def test_compare_trec_runs_allows_identical_run_tags_and_keeps_both_artifacts():
    baseline = BASELINE_RUN_TEXT.replace("baseline.run", "same-tag")
    candidate = CANDIDATE_RUN_TEXT.replace("candidate_run", "same-tag")

    report = compare_trec_runs(baseline, candidate, QRELS_TEXT, cutoff=1)

    assert report.baseline_run.run_id == "same-tag"
    assert report.candidate_run.run_id == "same-tag"
    assert report.baseline_run is not report.candidate_run


def test_compare_trec_runs_passes_metric_and_alternative_options():
    report = compare_trec_runs(
        BASELINE_RUN_TEXT,
        CANDIDATE_RUN_TEXT,
        QRELS_TEXT,
        cutoff=1,
        metric_name=PRECISION_AT_K_METRIC,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
    )

    assert report.comparison.significance.metric_name == PRECISION_AT_K_METRIC
    assert (
        report.comparison.significance.alternative
        == CANDIDATE_GREATER_ALTERNATIVE
    )
    assert report.comparison.significance.mean_difference == 1.0


def test_compare_trec_runs_result_is_immutable():
    report = compare_trec_runs(
        BASELINE_RUN_TEXT,
        CANDIDATE_RUN_TEXT,
        QRELS_TEXT,
        cutoff=1,
    )

    with pytest.raises(FrozenInstanceError):
        report.baseline_run = report.candidate_run


def test_compare_trec_runs_propagates_baseline_query_set_mismatch():
    baseline_without_query_b = """
    query-a Q0 irrelevant-a 1 0.9 baseline
    query-a Q0 relevant-a 2 0.4 baseline
    """

    with pytest.raises(ValueError, match="query sets must match"):
        compare_trec_runs(
            baseline_without_query_b,
            CANDIDATE_RUN_TEXT,
            QRELS_TEXT,
            cutoff=1,
        )


def test_compare_trec_runs_propagates_candidate_query_set_mismatch():
    candidate_without_query_b = """
    query-a Q0 relevant-a 1 0.9 candidate
    query-a Q0 irrelevant-a 2 0.4 candidate
    """

    with pytest.raises(ValueError, match="query sets must match"):
        compare_trec_runs(
            BASELINE_RUN_TEXT,
            candidate_without_query_b,
            QRELS_TEXT,
            cutoff=1,
        )


@pytest.mark.parametrize(
    ("baseline", "candidate", "qrels", "message"),
    [
        (
            "query-a Q0 doc 0 1.0 run\n",
            CANDIDATE_RUN_TEXT,
            QRELS_TEXT,
            "rank must be a positive integer",
        ),
        (
            BASELINE_RUN_TEXT,
            "query-a X doc 1 1.0 run\n",
            QRELS_TEXT,
            "second field must be Q0",
        ),
        (
            BASELINE_RUN_TEXT,
            CANDIDATE_RUN_TEXT,
            "query-a 0 doc 1.5\n",
            "relevance must be an integer",
        ),
    ],
)
def test_compare_trec_runs_propagates_precise_artifact_errors(
    baseline,
    candidate,
    qrels,
    message,
):
    with pytest.raises(ValueError, match=message):
        compare_trec_runs(baseline, candidate, qrels, cutoff=1)


def _large_artifacts():
    qrels_lines = ["# large judged set"]
    baseline_lines = ["# large baseline"]
    candidate_lines = ["# large candidate"]
    for index in range(17):
        query_id = f"query-{index}"
        relevant_id = f"relevant-{index}"
        irrelevant_id = f"irrelevant-{index}"
        qrels_lines.extend(
            [
                f"{query_id} 0 {relevant_id} 1",
                f"{query_id} 0 {irrelevant_id} 0",
            ]
        )
        if index < 11:
            baseline_scores = (0.4, 0.9)
            candidate_scores = (0.9, 0.4)
        else:
            baseline_scores = (0.9, 0.4)
            candidate_scores = (0.4, 0.9)
        baseline_lines.extend(
            [
                f"{query_id} Q0 {relevant_id} 1 {baseline_scores[0]} baseline",
                f"{query_id} Q0 {irrelevant_id} 2 {baseline_scores[1]} baseline",
            ]
        )
        candidate_lines.extend(
            [
                f"{query_id} Q0 {relevant_id} 1 {candidate_scores[0]} candidate",
                f"{query_id} Q0 {irrelevant_id} 2 {candidate_scores[1]} candidate",
            ]
        )
    return (
        "\n".join(baseline_lines) + "\n",
        "\n".join(candidate_lines) + "\n",
        "\n".join(qrels_lines) + "\n",
    )


def test_compare_trec_runs_passes_monte_carlo_count_and_seed():
    baseline, candidate, qrels = _large_artifacts()

    first = compare_trec_runs(
        baseline,
        candidate,
        qrels,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        randomization_count=300,
        random_seed=19,
    )
    second = compare_trec_runs(
        baseline,
        candidate,
        qrels,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        randomization_count=300,
        random_seed=19,
    )

    assert first == second
    assert first.comparison.significance.method == MONTE_CARLO_RANDOMIZATION_METHOD
    assert first.comparison.significance.randomizations_evaluated == 300
    assert first.comparison.significance.random_seed == 19
    assert 0.0 < first.comparison.significance.p_value < 1.0
