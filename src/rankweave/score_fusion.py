"""Fusion functions for hybrid (lexical + semantic) retrieval.

Default strategy: a convex combination of theoretically min-max
normalized channel scores ("TM2C2"; Bruch, Gai & Ingber 2023,
*An Analysis of Fusion Functions for Hybrid Retrieval*, ACM TOIS
42(1), arXiv:2210.11934). Their analysis shows TM2C2 outperforms
Reciprocal Rank Fusion in- and out-of-domain, is robust for alpha in
[0.6, 0.8] without training data, and — unlike RRF — preserves the
score distribution (Lipschitz continuity).

Bruch et al. analyze a lexical+semantic pair and note in §3.1 that
much of the analysis extends directly to multiple retrieval systems.
``weighted_convex_combination_score`` exposes that N-channel form for
already-normalized scores and explicit convex weights.

Reciprocal Rank Fusion (Cormack, Clarke & Büttcher 2009,
*Reciprocal Rank Fusion outperforms Condorcet and individual Rank
Learning Methods*, SIGIR) is the non-parametric alternative for
channels that expose only ranks (learned-sparse or external
channels), selected via ``FusionSettings.strategy_name``.

The convex strategy assumes each channel score has *theoretical*
bounds, so no per-query data-dependent normalization is needed. Two
bound constants ship for the common lexical+dense pairing, but they
are just ``(lower, upper)`` tuples — pass your own to
``theoretical_min_max_normalize`` for any bounded scoring function:

- ``WORD_SIMILARITY_THEORETICAL_BOUNDS``  = (0.0, 1.0) — e.g. a
  character-trigram word-similarity such as PostgreSQL ``pg_trgm``.
- ``COSINE_DISTANCE_THEORETICAL_BOUNDS`` = (0.0, 2.0) — cosine
  distance for unit-norm vectors, e.g. a pgvector ``<=>`` channel;
  fuse_channel_scores inverts it so smaller distance scores higher.
"""

import math
import operator
from collections.abc import Mapping
from dataclasses import dataclass

WORD_SIMILARITY_THEORETICAL_BOUNDS = (0.0, 1.0)
COSINE_DISTANCE_THEORETICAL_BOUNDS = (0.0, 2.0)

CONVEX_COMBINATION_STRATEGY = "convex_combination"
RECIPROCAL_RANK_STRATEGY = "reciprocal_rank_fusion"

_SUPPORTED_STRATEGY_NAMES = frozenset(
    {CONVEX_COMBINATION_STRATEGY, RECIPROCAL_RANK_STRATEGY}
)


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


@dataclass(frozen=True)
class FusionSettings:
    """Tunable fusion parameters (immutable; construct one per query set)."""

    strategy_name: str = CONVEX_COMBINATION_STRATEGY
    # Weight of the semantic channel; 0.7 is the midpoint of the
    # robust [0.6, 0.8] range reported by Bruch et al. (2023).
    semantic_weight_alpha: float = 0.7
    # RRF eta; 60 per Cormack et al. (2009).
    rank_constant_eta: int = 60

    def __post_init__(self) -> None:
        if self.strategy_name not in _SUPPORTED_STRATEGY_NAMES:
            raise ValueError(
                "strategy_name must be one of "
                f"{sorted(_SUPPORTED_STRATEGY_NAMES)}, got {self.strategy_name!r}"
            )
        _require_unit_interval(
            self.semantic_weight_alpha, "semantic_weight_alpha"
        )
        _require_positive_integer(self.rank_constant_eta, "rank_constant_eta")


def theoretical_min_max_normalize(
    score: float, bounds: tuple[float, float]
) -> float:
    """Scale a score to [0, 1] using the scoring function's theoretical bounds.

    Using theoretical rather than observed bounds keeps the transform
    stable across queries and candidate sets (Bruch et al. 2023, §4.2).
    Out-of-range finite inputs (floating-point drift) are clamped;
    NaN and infinities are rejected.
    """
    lower_bound, upper_bound = bounds
    _require_finite(score, "score")
    if not math.isfinite(lower_bound) or not math.isfinite(upper_bound):
        raise ValueError("bounds must be finite")
    if upper_bound <= lower_bound:
        raise ValueError("bounds must satisfy upper > lower")
    normalized = (score - lower_bound) / (upper_bound - lower_bound)
    return min(1.0, max(0.0, normalized))


def convex_combination_score(
    semantic_score: float | None,
    lexical_score: float | None,
    semantic_weight_alpha: float,
) -> float:
    """TM2C2 fusion over already-normalized [0, 1] channel scores.

    A channel absent for a candidate (e.g. no embedding stored yet)
    contributes its theoretical minimum, 0 — absent evidence is the
    infimum, not a missing value to impute. Supplied scores and the
    semantic weight must be finite values in [0, 1].
    """
    if semantic_score is not None:
        _require_unit_interval(semantic_score, "semantic_score")
    if lexical_score is not None:
        _require_unit_interval(lexical_score, "lexical_score")
    _require_unit_interval(semantic_weight_alpha, "semantic_weight_alpha")
    semantic_component = semantic_score if semantic_score is not None else 0.0
    lexical_component = lexical_score if lexical_score is not None else 0.0
    return (
        semantic_weight_alpha * semantic_component
        + (1.0 - semantic_weight_alpha) * lexical_component
    )


def weighted_convex_combination_score(
    channel_scores: Mapping[str, float | None],
    channel_weights: Mapping[str, float],
) -> float:
    """Fuse any number of normalized channels with convex weights.

    ``channel_weights`` defines the complete channel set. Its values
    must be non-negative and sum to 1 (within floating-point tolerance).
    ``channel_scores`` may omit channels or map them to ``None``; absent
    evidence contributes the theoretical minimum, 0. A score supplied
    without a corresponding weight is rejected as a configuration error.
    All supplied scores and weights must be finite.
    """
    score_channels_without_weights = set(channel_scores) - set(channel_weights)
    if score_channels_without_weights:
        raise ValueError(
            "channel scores contain channels without weights: "
            f"{sorted(score_channels_without_weights)!r}"
        )
    for channel_name, channel_weight in channel_weights.items():
        _require_finite(
            channel_weight, f"weight for channel {channel_name!r}"
        )
        if channel_weight < 0.0:
            raise ValueError("channel weights must be non-negative")
    total_weight = math.fsum(channel_weights.values())
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("channel weights must sum to 1")
    for channel_name, channel_score in channel_scores.items():
        if channel_score is not None:
            _require_unit_interval(
                channel_score, f"score for channel {channel_name!r}"
            )

    weighted_components = []
    for channel_name, channel_weight in channel_weights.items():
        channel_score = channel_scores.get(channel_name)
        score_or_infimum = 0.0 if channel_score is None else channel_score
        weighted_components.append(channel_weight * score_or_infimum)
    return math.fsum(weighted_components)


def reciprocal_rank_fusion_score(
    channel_ranks: dict[str, int], rank_constant_eta: int = 60
) -> float:
    """RRF over positive integer 1-based ranks: sum of 1 / (eta + rank)."""
    validated_eta = _require_positive_integer(
        rank_constant_eta, "rank_constant_eta"
    )
    fused_score = 0.0
    for channel_name, one_based_rank in channel_ranks.items():
        validated_rank = _require_positive_integer(
            one_based_rank, f"rank for channel {channel_name!r}"
        )
        fused_score += 1.0 / (validated_eta + validated_rank)
    return fused_score


def fuse_channel_scores(
    *,
    word_similarity_score: float | None,
    cosine_distance: float | None,
    channel_ranks: dict[str, int],
    settings: FusionSettings,
) -> float:
    """Fuse one candidate's channel evidence into a single score.

    ``word_similarity_score`` and ``cosine_distance`` are the raw
    channel outputs (None when the channel did not produce this
    candidate); ``channel_ranks`` are the candidate's 1-based ranks in
    the channels that returned it, used by the RRF strategy.
    """
    if settings.strategy_name == RECIPROCAL_RANK_STRATEGY:
        if not channel_ranks:
            return 0.0
        return reciprocal_rank_fusion_score(
            channel_ranks, settings.rank_constant_eta
        )

    normalized_lexical_score = (
        theoretical_min_max_normalize(
            word_similarity_score, WORD_SIMILARITY_THEORETICAL_BOUNDS
        )
        if word_similarity_score is not None
        else None
    )
    # Cosine *distance* decreases as relevance increases; invert inside
    # the theoretical [0, 2] range so 1.0 means identical direction.
    normalized_semantic_score = (
        1.0
        - theoretical_min_max_normalize(
            cosine_distance, COSINE_DISTANCE_THEORETICAL_BOUNDS
        )
        if cosine_distance is not None
        else None
    )
    return convex_combination_score(
        normalized_semantic_score,
        normalized_lexical_score,
        settings.semantic_weight_alpha,
    )
