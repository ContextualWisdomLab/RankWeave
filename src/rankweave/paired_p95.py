"""Paired empirical p95 evidence from a caller-owned unit resampling plan."""

from collections.abc import Sequence
from dataclasses import dataclass

from rankweave import _rankweave_core
from rankweave._validation import _require_finite, _require_positive_integer


@dataclass(frozen=True)
class PairedP95Report:
    """Replay results, not certification of the supplied sampling design."""

    schema_version: str
    algorithm_version: str
    ordered_input_digest: str
    observation_count: int
    resampling_unit_count: int
    baseline_p95: float
    candidate_p95: float
    p95_difference: float
    interval_low: float
    interval_high: float
    resampled_differences: tuple[float, ...]
    resample_observation_counts: tuple[int, ...]


def compare_paired_p95(
    observation_pairs: Sequence[tuple[str, float, float]],
    resampling_units: Sequence[Sequence[str]],
    unit_draws: Sequence[Sequence[int]],
    *,
    max_resample_observations: int,
) -> PairedP95Report:
    """Replay whole paired units; return candidate-minus-baseline p95 evidence.

    Pairs contain an opaque observation ID, baseline value, and candidate value.
    Units partition IDs exactly; each draw has one zero-based unit index per
    original unit, with replacement. The caller owns design validity and draws.
    Quantiles use the inverse empirical CDF, without interpolating observations.
    """
    pairs = list(observation_pairs)
    for _, baseline_value, candidate_value in pairs:
        _require_finite(baseline_value, "baseline_value")
        _require_finite(candidate_value, "candidate_value")
    row_bound = _require_positive_integer(
        max_resample_observations, "max_resample_observations"
    )
    units = [list(unit_members) for unit_members in resampling_units]
    draws = [list(unit_draw) for unit_draw in unit_draws]
    for unit_draw in draws:
        for unit_index in unit_draw:
            if isinstance(unit_index, bool) or not isinstance(unit_index, int):
                raise ValueError("unit indices must be integers, not booleans")
            if not 0 <= unit_index < len(units):
                raise ValueError("draw contains an unknown unit")
    schema, algorithm, digest, counts, values, differences, row_counts = (
        _rankweave_core.compare_paired_p95(
            pairs,
            units,
            draws,
            row_bound,
        )
    )
    return PairedP95Report(
        schema,
        algorithm,
        digest,
        *counts,
        *values,
        tuple(differences),
        tuple(row_counts),
    )
