from datetime import datetime, timezone

import pytest

from rankweave import (
    WeightedConvexBacktestWindowDefinition,
    backtest_weighted_convex_fusion,
)

UTC = timezone.utc


def test_backtest_rejects_training_on_a_query_before_its_future_assessment():
    results = {
        query_id: {
            "lexical": [(f"relevant-{query_id}", 1.0)],
            "dense": [(f"relevant-{query_id}", 1.0)],
        }
        for query_id in ("q0", "q1", "q2", "q3", "q4", "q5")
    }
    judgments = {
        query_id: {f"relevant-{query_id}": 1}
        for query_id in results
    }
    available_times = {
        query_id: datetime(2026, 1, day, tzinfo=UTC)
        for query_id, day in zip(results, (1, 2, 3, 4, 5, 6), strict=True)
    }
    windows = (
        WeightedConvexBacktestWindowDefinition(
            window_id="first",
            training_query_ids=("q0", "q1"),
            held_out_query_ids=("q2",),
        ),
        WeightedConvexBacktestWindowDefinition(
            window_id="second",
            training_query_ids=("q0", "q1", "q2", "q4"),
            held_out_query_ids=("q3",),
        ),
        WeightedConvexBacktestWindowDefinition(
            window_id="third",
            training_query_ids=("q0", "q1", "q2", "q3"),
            held_out_query_ids=("q4", "q5"),
        ),
    )

    with pytest.raises(
        ValueError,
        match="training before their held-out window",
    ):
        backtest_weighted_convex_fusion(
            results,
            judgments,
            {"equal": {"lexical": 0.5, "dense": 0.5}},
            available_times,
            windows,
            cutoff=1,
        )
