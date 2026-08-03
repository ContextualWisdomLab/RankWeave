"""Shared numeric validation primitives for RankWeave fusion APIs."""

import math
import operator


def _require_finite(value: float, label: str) -> None:
    """Reject IEEE non-finite values before comparisons or arithmetic."""
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


def _require_unit_interval(value: float, label: str) -> None:
    """Require a finite value in the closed unit interval."""
    _require_finite(value, label)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")


def _require_positive_integer(value: int, label: str) -> int:
    """Return a validated positive integer, rejecting booleans and floats."""
    _require_finite(value, label)
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    try:
        integer_value = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if integer_value < 1:
        raise ValueError(f"{label} must be >= 1")
    return integer_value
