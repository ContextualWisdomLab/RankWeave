import math
from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from rankweave.comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    MONTE_CARLO_RANDOMIZATION_METHOD,
)
from rankweave.trec_family_comparison import (
    TrecCandidateComparison,
    TrecRunFamilyComparisonReport,
    compare_trec_run_family,
)

QRELS_TEXT = """
query-a 0 relevant-a 1
query-a 0 irrelevant-a 0
query-b 0 relevant-b 1
query-b 0 irrelevant-b 0
"""

BASELINE_RUN = """
query-a Q0 irrelevant-a 1 0.9 shared-tag
query-a Q0 relevant-a 2 0.2 shared-tag
query-b Q0 irrelevant-b 1 0.8 shared-tag
query-b Q0 relevant-b 2 0.1 shared-tag
"""

STRONG_CANDIDATE = """
query-a Q0 relevant-a 1 0.9 shared-tag
query-a Q0 irrelevant-a 2 0.2 shared-tag
query-b Q0 relevant-b 1 0.8 shared-tag
query-b Q0 irrelevant-b 2 0.1 shared-tag
"""

PARTIAL_CANDIDATE = """
query-a Q0 relevant-a 1 0.9 partial
query-a Q0 irrelevant-a 2 0.2 partial
query-b Q0 irrelevant-b 1 0.8 partial
query-b Q0 relevant-b 2 0.1 partial
"""

EQUAL_CANDIDATE = BASELINE_RUN


def test_family_comparison_applies_hand_checked_holm_adjustment():
    report = compare_trec_run_family(
        BASELINE_RUN,
        {
            "strong": STRONG_CANDIDATE,
            "partial": PARTIAL_CANDIDATE,
            "equal": EQUAL_CANDIDATE,
        },
        QRELS_TEXT,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        familywise_alpha=0.8,
    )

    assert isinstance(report, TrecRunFamilyComparisonReport)
    assert report.baseline_run.run_id == "shared-tag"
    assert report.familywise_alpha == 0.8
    assert [entry.candidate_id for entry in report.candidates] == [
        "strong",
        "partial",
        "equal",
    ]
    assert [
        entry.comparison.significance.mean_difference
        for entry in report.candidates
    ] == pytest.approx([1.0, 0.5, 0.0])
    assert [entry.raw_p_value for entry in report.candidates] == pytest.approx(
        [0.25, 0.5, 1.0]
    )
    assert [
        entry.holm_adjusted_p_value for entry in report.candidates
    ] == pytest.approx([0.75, 1.0, 1.0])
    assert [
        entry.rejected_at_familywise_alpha for entry in report.candidates
    ] == [True, False, False]
    assert report.candidates[0].candidate_run.run_id == "shared-tag"
    assert report.candidates[0].candidate_run is not report.baseline_run


def test_family_comparison_preserves_tie_input_order():
    report = compare_trec_run_family(
        BASELINE_RUN,
        {
            "first": STRONG_CANDIDATE,
            "second": STRONG_CANDIDATE.replace("shared-tag", "second"),
            "equal": EQUAL_CANDIDATE,
        },
        QRELS_TEXT,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        familywise_alpha=0.8,
    )

    assert [entry.candidate_id for entry in report.candidates] == [
        "first",
        "second",
        "equal",
    ]
    assert [entry.holm_adjusted_p_value for entry in report.candidates] == [
        0.75,
        0.75,
        1.0,
    ]


def test_familywise_alpha_changes_only_rejection_decisions():
    report = compare_trec_run_family(
        BASELINE_RUN,
        {"strong": STRONG_CANDIDATE},
        QRELS_TEXT,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        familywise_alpha=0.2,
    )

    candidate = report.candidates[0]
    assert candidate.comparison.significance.mean_difference == 1.0
    assert candidate.raw_p_value == 0.25
    assert candidate.holm_adjusted_p_value == 0.25
    assert candidate.rejected_at_familywise_alpha is False


def test_family_comparison_records_are_immutable():
    report = compare_trec_run_family(
        BASELINE_RUN,
        {"strong": STRONG_CANDIDATE},
        QRELS_TEXT,
        cutoff=1,
    )

    assert isinstance(report.candidates[0], TrecCandidateComparison)
    with pytest.raises(FrozenInstanceError):
        report.familywise_alpha = 0.1
    with pytest.raises(FrozenInstanceError):
        report.candidates[0].raw_p_value = 0.0


@pytest.mark.parametrize(
    ("candidate_runs", "message"),
    [
        ({}, "at least one candidate"),
        ([], "must be a mapping"),
    ],
)
def test_family_comparison_rejects_invalid_candidate_collection(
    candidate_runs,
    message,
):
    with pytest.raises(ValueError, match=message):
        compare_trec_run_family(
            BASELINE_RUN,
            candidate_runs,
            QRELS_TEXT,
            cutoff=1,
        )


@pytest.mark.parametrize("invalid_alpha", [0.0, -0.1, 1.1, math.nan, True, "0.05"])
def test_family_comparison_rejects_invalid_familywise_alpha(invalid_alpha):
    with pytest.raises(ValueError, match="familywise_alpha"):
        compare_trec_run_family(
            BASELINE_RUN,
            {"candidate": STRONG_CANDIDATE},
            QRELS_TEXT,
            cutoff=1,
            familywise_alpha=invalid_alpha,
        )


def test_family_comparison_prefixes_candidate_artifact_error():
    with pytest.raises(ValueError, match="candidate 'broken'.*rank must be"):
        compare_trec_run_family(
            BASELINE_RUN,
            {"broken": "query-a Q0 doc 0 1.0 broken\n"},
            QRELS_TEXT,
            cutoff=1,
        )


def test_family_comparison_prefixes_candidate_query_set_error():
    query_a_only = """
    query-a Q0 relevant-a 1 0.9 partial
    query-a Q0 irrelevant-a 2 0.2 partial
    """
    with pytest.raises(ValueError, match="candidate 'incomplete'.*query sets"):
        compare_trec_run_family(
            BASELINE_RUN,
            {"incomplete": query_a_only},
            QRELS_TEXT,
            cutoff=1,
        )


def test_family_comparison_preserves_baseline_and_qrels_errors():
    with pytest.raises(ValueError, match="rank must be"):
        compare_trec_run_family(
            "query-a Q0 doc 0 1.0 baseline\n",
            {"candidate": STRONG_CANDIDATE},
            QRELS_TEXT,
            cutoff=1,
        )
    with pytest.raises(ValueError, match="relevance must be an integer"):
        compare_trec_run_family(
            BASELINE_RUN,
            {"candidate": STRONG_CANDIDATE},
            "query-a 0 doc 1.5\n",
            cutoff=1,
        )


class _UnhashableCandidateMapping(Mapping):
    def __getitem__(self, key):
        return STRONG_CANDIDATE

    def __iter__(self):
        return iter((["unhashable"],))

    def __len__(self):
        return 1

    def items(self):
        return [(["unhashable"], STRONG_CANDIDATE)]


def test_family_comparison_rejects_unhashable_candidate_id():
    with pytest.raises(ValueError, match="candidate identifiers must be hashable"):
        compare_trec_run_family(
            BASELINE_RUN,
            _UnhashableCandidateMapping(),
            QRELS_TEXT,
            cutoff=1,
        )


def _large_family_artifacts():
    qrels_lines = []
    baseline_lines = []
    candidate_lines = []
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


def test_family_comparison_passes_monte_carlo_options():
    baseline, candidate, qrels = _large_family_artifacts()

    report = compare_trec_run_family(
        baseline,
        {"candidate": candidate},
        qrels,
        cutoff=1,
        alternative=CANDIDATE_GREATER_ALTERNATIVE,
        randomization_count=350,
        random_seed=23,
    )

    significance = report.candidates[0].comparison.significance
    assert significance.method == MONTE_CARLO_RANDOMIZATION_METHOD
    assert significance.randomizations_evaluated == 350
    assert significance.random_seed == 23
    assert report.candidates[0].holm_adjusted_p_value == significance.p_value
