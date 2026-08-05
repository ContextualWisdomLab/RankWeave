from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from rankweave import (
    WeightedConvexBacktestReport,
    WeightedConvexBacktestWindow,
    WeightedConvexBacktestWindowDefinition,
    backtest_weighted_convex_fusion,
)
from rankweave.tuning import SUPPORTED_TUNING_OBJECTIVES

UTC = timezone.utc


def _scores(relevant_item, other_item, *, preferred_channel):
    if preferred_channel == "lexical":
        return {
            "lexical": [(relevant_item, 1.0), (other_item, 0.0)],
            "dense": [(other_item, 1.0), (relevant_item, 0.0)],
        }
    return {
        "lexical": [(other_item, 1.0), (relevant_item, 0.0)],
        "dense": [(relevant_item, 1.0), (other_item, 0.0)],
    }


def _scored_results():
    return {
        "q0": _scores("r0", "x0", preferred_channel="lexical"),
        "q1": _scores("r1", "x1", preferred_channel="lexical"),
        "q2": _scores("r2", "x2", preferred_channel="dense"),
        "q3": _scores("r3", "x3", preferred_channel="dense"),
        "q4": _scores("r4", "x4", preferred_channel="dense"),
        "q5": _scores("r5", "x5", preferred_channel="dense"),
    }


def _judgments():
    return {f"q{index}": {f"r{index}": 3} for index in range(6)}


def _available_times():
    return {
        "q0": datetime(2026, 1, 1, 10, tzinfo=UTC),
        "q1": datetime(2026, 1, 2, 10, tzinfo=UTC),
        "q2": datetime(2026, 1, 3, 10, tzinfo=UTC),
        "q3": datetime(2026, 1, 3, 11, tzinfo=UTC),
        "q4": datetime(2026, 1, 4, 10, tzinfo=UTC),
        "q5": datetime(2026, 1, 4, 11, tzinfo=UTC),
    }


def _candidate_weights():
    return {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    }


def _windows():
    return (
        WeightedConvexBacktestWindowDefinition(
            window_id="window-1",
            training_query_ids=("q0", "q1"),
            held_out_query_ids=("q2", "q3"),
        ),
        WeightedConvexBacktestWindowDefinition(
            window_id="window-2",
            training_query_ids=("q0", "q1", "q2", "q3"),
            held_out_query_ids=("q4", "q5"),
        ),
    )


def _backtest(**overrides):
    arguments = {
        "channel_results_by_query": _scored_results(),
        "relevance_by_query": _judgments(),
        "candidate_channel_weights": _candidate_weights(),
        "available_time_by_query": _available_times(),
        "windows": _windows(),
        "cutoff": 1,
    }
    arguments.update(overrides)
    return backtest_weighted_convex_fusion(**arguments)


def test_backtest_preserves_temporal_evidence_and_original_oos_order():
    report = _backtest()

    assert report.initial_training_query_ids == ("q0", "q1")
    assert [window.window_id for window in report.windows] == [
        "window-1",
        "window-2",
    ]

    first_window = report.windows[0]
    assert first_window.training_query_ids == ("q0", "q1")
    assert first_window.held_out_query_ids == ("q2", "q3")
    assert first_window.training_available_time_max == datetime(
        2026, 1, 2, 10, tzinfo=UTC
    )
    assert first_window.held_out_available_time_min == datetime(
        2026, 1, 3, 10, tzinfo=UTC
    )
    assert first_window.held_out_available_time_max == datetime(
        2026, 1, 3, 11, tzinfo=UTC
    )
    assert first_window.tuning.best_policy_id == "lexical-heavy"
    assert first_window.held_out_rankings == (
        ("q2", ("x2",)),
        ("q3", ("x3",)),
    )
    assert first_window.held_out_evaluation.aggregate.mean_ndcg_at_k == 0.0

    second_window = report.windows[1]
    assert second_window.training_query_ids == ("q0", "q1", "q2", "q3")
    assert second_window.held_out_query_ids == ("q4", "q5")
    assert second_window.tuning.best_policy_id == "dense-heavy"
    assert second_window.held_out_rankings == (
        ("q4", ("r4",)),
        ("q5", ("r5",)),
    )
    assert second_window.held_out_evaluation.aggregate.mean_ndcg_at_k == 1.0

    assert report.out_of_sample_rankings == (
        ("q2", ("x2",)),
        ("q3", ("x3",)),
        ("q4", ("r4",)),
        ("q5", ("r5",)),
    )
    assert report.out_of_sample_evaluation.aggregate.query_count == 4
    assert report.out_of_sample_evaluation.aggregate.mean_ndcg_at_k == 0.5
    assert report.final_tuning.best_policy_id == "dense-heavy"
    assert report.final_tuning.best_objective_score == pytest.approx(4 / 6)


@pytest.mark.parametrize("objective_name", sorted(SUPPORTED_TUNING_OBJECTIVES))
def test_backtest_supports_every_existing_tuning_objective(objective_name):
    report = _backtest(objective_name=objective_name)

    assert report.objective_name == objective_name
    assert report.windows[0].tuning.objective_name == objective_name
    assert report.windows[1].tuning.objective_name == objective_name
    assert report.final_tuning.objective_name == objective_name


def test_backtest_normalizes_timezone_aware_availability_to_utc():
    available_times = _available_times()
    korea_time = timezone(timedelta(hours=9))
    available_times["q0"] = datetime(2026, 1, 1, 19, tzinfo=korea_time)

    report = _backtest(available_time_by_query=available_times)

    assert report.windows[0].training_available_time_max.tzinfo is UTC
    assert report.windows[0].training_available_time_max == datetime(
        2026, 1, 2, 10, tzinfo=UTC
    )


@pytest.mark.parametrize(
    ("query_id", "invalid_time", "message"),
    [
        ("q0", "2026-01-01T10:00:00Z", "must be a datetime"),
        ("q0", datetime(2026, 1, 1, 10), "timezone-aware"),
    ],
)
def test_backtest_rejects_invalid_availability_time(
    query_id, invalid_time, message
):
    available_times = _available_times()
    available_times[query_id] = invalid_time

    with pytest.raises(ValueError, match=message):
        _backtest(available_time_by_query=available_times)


def test_backtest_rejects_availability_query_set_mismatch():
    available_times = _available_times()
    del available_times["q4"]
    available_times["extra"] = datetime(2026, 1, 5, tzinfo=UTC)

    with pytest.raises(ValueError, match="availability query sets must match"):
        _backtest(available_time_by_query=available_times)


def test_backtest_requires_at_least_one_window():
    with pytest.raises(ValueError, match="at least one assessment window"):
        _backtest(windows=())


def test_backtest_rejects_duplicate_window_identifier():
    windows = list(_windows())
    windows[1] = WeightedConvexBacktestWindowDefinition(
        window_id="window-1",
        training_query_ids=windows[1].training_query_ids,
        held_out_query_ids=windows[1].held_out_query_ids,
    )

    with pytest.raises(ValueError, match="duplicate window identifier"):
        _backtest(windows=windows)


def test_backtest_rejects_unhashable_window_identifier():
    windows = list(_windows())
    windows[0] = WeightedConvexBacktestWindowDefinition(
        window_id=["not-hashable"],
        training_query_ids=windows[0].training_query_ids,
        held_out_query_ids=windows[0].held_out_query_ids,
    )

    with pytest.raises(ValueError, match="window identifier must be hashable"):
        _backtest(windows=windows)


@pytest.mark.parametrize("query_side", ["training", "held-out"])
def test_backtest_rejects_duplicate_query_within_window(query_side):
    first, second = _windows()
    if query_side == "training":
        first = WeightedConvexBacktestWindowDefinition(
            window_id=first.window_id,
            training_query_ids=("q0", "q0"),
            held_out_query_ids=first.held_out_query_ids,
        )
    else:
        first = WeightedConvexBacktestWindowDefinition(
            window_id=first.window_id,
            training_query_ids=first.training_query_ids,
            held_out_query_ids=("q2", "q2"),
        )

    with pytest.raises(ValueError, match=f"duplicate {query_side} query"):
        _backtest(windows=(first, second))


@pytest.mark.parametrize("query_side", ["training", "held-out"])
def test_backtest_rejects_empty_window_query_side(query_side):
    first, second = _windows()
    if query_side == "training":
        first = WeightedConvexBacktestWindowDefinition(
            window_id=first.window_id,
            training_query_ids=(),
            held_out_query_ids=first.held_out_query_ids,
        )
    else:
        first = WeightedConvexBacktestWindowDefinition(
            window_id=first.window_id,
            training_query_ids=first.training_query_ids,
            held_out_query_ids=(),
        )

    with pytest.raises(ValueError, match=f"non-empty {query_side}"):
        _backtest(windows=(first, second))


def test_backtest_rejects_unknown_query_identifier():
    first, second = _windows()
    first = WeightedConvexBacktestWindowDefinition(
        window_id=first.window_id,
        training_query_ids=("q0", "unknown"),
        held_out_query_ids=first.held_out_query_ids,
    )

    with pytest.raises(ValueError, match="unknown query identifiers"):
        _backtest(windows=(first, second))


def test_backtest_rejects_within_window_training_held_out_overlap():
    first, second = _windows()
    first = WeightedConvexBacktestWindowDefinition(
        window_id=first.window_id,
        training_query_ids=("q0", "q2"),
        held_out_query_ids=first.held_out_query_ids,
    )

    with pytest.raises(ValueError, match="training and held-out queries overlap"):
        _backtest(windows=(first, second))


@pytest.mark.parametrize("training_time", [
    datetime(2026, 1, 3, 10, tzinfo=UTC),
    datetime(2026, 1, 3, 12, tzinfo=UTC),
])
def test_backtest_rejects_same_time_or_future_training_evidence(training_time):
    available_times = _available_times()
    available_times["q1"] = training_time

    with pytest.raises(ValueError, match="training evidence must precede"):
        _backtest(available_time_by_query=available_times)


def test_backtest_rejects_query_held_out_more_than_once():
    first, second = _windows()
    second = WeightedConvexBacktestWindowDefinition(
        window_id=second.window_id,
        training_query_ids=second.training_query_ids,
        held_out_query_ids=("q3", "q5"),
    )

    with pytest.raises(ValueError, match="held out more than once"):
        _backtest(windows=(first, second))


def test_backtest_rejects_non_monotone_held_out_time_ranges():
    available_times = _available_times()
    available_times["q4"] = datetime(2026, 1, 3, 10, 30, tzinfo=UTC)

    with pytest.raises(ValueError, match="held-out time ranges must be ordered"):
        _backtest(available_time_by_query=available_times)


def test_backtest_rejects_query_missing_from_warmup_and_assessment():
    first, second = _windows()
    second = WeightedConvexBacktestWindowDefinition(
        window_id=second.window_id,
        training_query_ids=("q0", "q1", "q2", "q3", "q5"),
        held_out_query_ids=("q4",),
    )

    with pytest.raises(ValueError, match="queries are neither initial training"):
        _backtest(windows=(first, second))


def test_backtest_rejects_initial_training_query_later_held_out():
    first, second = _windows()
    second = WeightedConvexBacktestWindowDefinition(
        window_id=second.window_id,
        training_query_ids=("q1", "q2", "q3"),
        held_out_query_ids=("q0", "q4", "q5"),
    )

    with pytest.raises(ValueError, match="initial training queries may not be held out"):
        _backtest(windows=(first, second))


@pytest.mark.parametrize("invalid_cutoff", [0, 1.5, True])
def test_backtest_rejects_invalid_cutoff(invalid_cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        _backtest(cutoff=invalid_cutoff)


def test_backtest_rejects_unsupported_objective():
    with pytest.raises(ValueError, match="objective_name must be one of"):
        _backtest(objective_name="mean_map_at_k")


def test_backtest_rejects_empty_policy_family():
    with pytest.raises(ValueError, match="at least one candidate"):
        _backtest(candidate_channel_weights={})


def test_backtest_propagates_invalid_weight_policy():
    with pytest.raises(ValueError, match="sum to 1"):
        _backtest(
            candidate_channel_weights={
                "invalid": {"lexical": 0.4, "dense": 0.4}
            }
        )


def test_backtest_propagates_out_of_domain_score():
    results = _scored_results()
    results["q0"]["lexical"][0] = ("r0", 1.1)

    with pytest.raises(ValueError, match=r"score for channel 'lexical'.*\[0, 1\]"):
        _backtest(channel_results_by_query=results)


def test_backtest_propagates_duplicate_item_error():
    results = _scored_results()
    results["q0"]["lexical"] = [("r0", 1.0), ("r0", 0.5)]

    with pytest.raises(ValueError, match="contains duplicate item"):
        _backtest(channel_results_by_query=results)


def test_backtest_records_are_immutable_and_exported():
    definition = _windows()[0]
    report = _backtest()
    window = report.windows[0]

    assert isinstance(definition, WeightedConvexBacktestWindowDefinition)
    assert isinstance(window, WeightedConvexBacktestWindow)
    assert isinstance(report, WeightedConvexBacktestReport)
    with pytest.raises(FrozenInstanceError):
        definition.window_id = "other"
    with pytest.raises(FrozenInstanceError):
        window.window_id = "other"
    with pytest.raises(FrozenInstanceError):
        report.cutoff = 10
