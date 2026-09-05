"""Hand-checked paired quantile replay and complete-unit validation."""

import rankweave


def test_paired_p95_replays_whole_units_not_quantiles_of_differences():
    report = rankweave.compare_paired_p95(
        [("task-a", 1.0, 100.0), ("task-b", 100.0, 1.0), ("task-c", 2.0, 2.0)],
        [["task-a", "task-c"], ["task-b"]],
        [[0, 0], [1, 1], [0, 1]],
        max_resample_observations=4,
    )
    assert report.baseline_p95 == 100.0
    assert report.candidate_p95 == 100.0
    assert report.p95_difference == 0.0
    assert report.resampled_differences == (98.0, -99.0, 0.0)
    assert report.resample_observation_counts == (4, 2, 3)
    assert (report.interval_low, report.interval_high) == (-99.0, 98.0)
    assert (report.observation_count, report.resampling_unit_count) == (3, 2)
