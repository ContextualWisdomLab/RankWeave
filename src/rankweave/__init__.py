"""rankweave — language-agnostic hybrid-retrieval score fusion.

Pure-Python (stdlib-only) fusion of lexical, semantic, learned-sparse,
and other retrieval channels, complete-list fusion, and Unicode NFC query
normalization. Store-agnostic: bring your own channels; rankweave decides
how to combine their evidence.

Two fusion strategies, research-grounded (see ``docs/research/``):

- ``convex_combination`` (default, "TM2C2") — Bruch, Gai & Ingber
  2023 (arXiv:2210.11934): a convex combination of theoretically
  min-max normalized scores; robust, distribution-preserving, no
  training data needed. The public API supports both the common
  two-channel pairing and explicit N-channel convex weights.
- ``reciprocal_rank_fusion`` — Cormack, Clarke & Büttcher 2009: the
  non-parametric rank-only alternative, with equal- and convex-weighted
  complete-list APIs.

Quickstart::

    from rankweave import FusionSettings, fuse_channel_scores

    settings = FusionSettings()  # TM2C2, alpha=0.7
    score = fuse_channel_scores(
        word_similarity_score=0.62,   # lexical channel, [0, 1]
        cosine_distance=0.30,         # dense channel, [0, 2]
        channel_ranks={"lexical": 1, "dense": 1},
        settings=settings,
    )
"""

from rankweave.query_normalization import (
    DEFAULT_MAX_QUERY_CHARACTER_LENGTH,
    normalize_search_text,
)
from rankweave.ranked_list_fusion import (
    FusedRankedItem,
    FusedScoredItem,
    FusedWeightedRankedItem,
    WeightedChannelContribution,
    WeightedRankContribution,
    reciprocal_rank_fuse,
    weighted_convex_fuse,
    weighted_reciprocal_rank_fuse,
)
from rankweave.score_fusion import (
    CONVEX_COMBINATION_STRATEGY,
    COSINE_DISTANCE_THEORETICAL_BOUNDS,
    RECIPROCAL_RANK_STRATEGY,
    WORD_SIMILARITY_THEORETICAL_BOUNDS,
    FusionSettings,
    convex_combination_score,
    fuse_channel_scores,
    reciprocal_rank_fusion_score,
    theoretical_min_max_normalize,
    weighted_convex_combination_score,
    weighted_reciprocal_rank_fusion_score,
)

__version__ = "0.2.0"

__all__ = [
    "CONVEX_COMBINATION_STRATEGY",
    "COSINE_DISTANCE_THEORETICAL_BOUNDS",
    "DEFAULT_MAX_QUERY_CHARACTER_LENGTH",
    "RECIPROCAL_RANK_STRATEGY",
    "WORD_SIMILARITY_THEORETICAL_BOUNDS",
    "FusedRankedItem",
    "FusedScoredItem",
    "FusedWeightedRankedItem",
    "FusionSettings",
    "WeightedChannelContribution",
    "WeightedRankContribution",
    "convex_combination_score",
    "fuse_channel_scores",
    "normalize_search_text",
    "reciprocal_rank_fuse",
    "reciprocal_rank_fusion_score",
    "theoretical_min_max_normalize",
    "weighted_convex_combination_score",
    "weighted_convex_fuse",
    "weighted_reciprocal_rank_fuse",
    "weighted_reciprocal_rank_fusion_score",
    "__version__",
]
