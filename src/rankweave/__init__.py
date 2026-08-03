"""rankweave — language-agnostic retrieval fusion, evaluation, and tuning.

Pure-Python (stdlib-only) fusion of lexical, semantic, learned-sparse,
and other retrieval channels, complete-list fusion, ranked-effectiveness
evaluation, offline weight-policy tuning, strict TREC interchange, and Unicode
NFC query normalization. Store-agnostic: bring your own channels; rankweave
combines and evaluates their evidence.

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

from rankweave.evaluation import (
    AggregateRankingMetrics,
    QueryRankingMetrics,
    RankingEvaluationReport,
    RankingMetrics,
    evaluate_ranking,
    evaluate_rankings,
)
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
from rankweave.trec import (
    TrecQrelEntry,
    TrecQrels,
    TrecRun,
    TrecRunEntry,
    evaluate_trec_run,
    format_trec_qrels,
    format_trec_run,
    parse_trec_qrels,
    parse_trec_run,
)
from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    MEAN_PRECISION_OBJECTIVE,
    MEAN_RECALL_OBJECTIVE,
    MEAN_RECIPROCAL_RANK_OBJECTIVE,
    SUPPORTED_TUNING_OBJECTIVES,
    WeightedRRFTuningReport,
    WeightedRRFTuningTrial,
    tune_weighted_reciprocal_rank_fusion,
)

__version__ = "0.6.0"

__all__ = [
    "AggregateRankingMetrics",
    "CONVEX_COMBINATION_STRATEGY",
    "COSINE_DISTANCE_THEORETICAL_BOUNDS",
    "DEFAULT_MAX_QUERY_CHARACTER_LENGTH",
    "MEAN_NDCG_OBJECTIVE",
    "MEAN_PRECISION_OBJECTIVE",
    "MEAN_RECALL_OBJECTIVE",
    "MEAN_RECIPROCAL_RANK_OBJECTIVE",
    "RECIPROCAL_RANK_STRATEGY",
    "SUPPORTED_TUNING_OBJECTIVES",
    "WORD_SIMILARITY_THEORETICAL_BOUNDS",
    "FusedRankedItem",
    "FusedScoredItem",
    "FusedWeightedRankedItem",
    "FusionSettings",
    "QueryRankingMetrics",
    "RankingEvaluationReport",
    "RankingMetrics",
    "TrecQrelEntry",
    "TrecQrels",
    "TrecRun",
    "TrecRunEntry",
    "WeightedChannelContribution",
    "WeightedRRFTuningReport",
    "WeightedRRFTuningTrial",
    "WeightedRankContribution",
    "convex_combination_score",
    "evaluate_ranking",
    "evaluate_rankings",
    "evaluate_trec_run",
    "format_trec_qrels",
    "format_trec_run",
    "fuse_channel_scores",
    "normalize_search_text",
    "parse_trec_qrels",
    "parse_trec_run",
    "reciprocal_rank_fuse",
    "reciprocal_rank_fusion_score",
    "theoretical_min_max_normalize",
    "tune_weighted_reciprocal_rank_fusion",
    "weighted_convex_combination_score",
    "weighted_convex_fuse",
    "weighted_reciprocal_rank_fuse",
    "weighted_reciprocal_rank_fusion_score",
    "__version__",
]
