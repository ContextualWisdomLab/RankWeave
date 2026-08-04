"""rankweave — retrieval fusion, evaluation, comparison, and tuning.

Pure-Python (stdlib-only) fusion of lexical, semantic, learned-sparse,
and other retrieval channels, complete-list fusion, ranked-effectiveness
evaluation, paired statistical comparison, offline weight-policy tuning,
strict TREC interchange, direct TREC run comparison, and Unicode NFC query
normalization. Store-agnostic: bring your own channels; rankweave combines and
evaluates their evidence.

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

from rankweave.comparison import (
    CANDIDATE_GREATER_ALTERNATIVE,
    CANDIDATE_LESS_ALTERNATIVE,
    DEFAULT_RANDOM_SEED,
    DEFAULT_RANDOMIZATION_COUNT,
    EXACT_RANDOMIZATION_METHOD,
    EXACT_RANDOMIZATION_PAIR_LIMIT,
    MONTE_CARLO_RANDOMIZATION_METHOD,
    NDCG_AT_K_METRIC,
    PRECISION_AT_K_METRIC,
    RECALL_AT_K_METRIC,
    RECIPROCAL_RANK_AT_K_METRIC,
    SUPPORTED_COMPARISON_ALTERNATIVES,
    SUPPORTED_COMPARISON_METRICS,
    TWO_SIDED_ALTERNATIVE,
    PairedRandomizationResult,
    QueryMetricDifference,
    RankingComparisonReport,
    compare_ranking_reports,
    compare_rankings,
)
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
from rankweave.trec_comparison import (
    TrecRunComparisonReport,
    compare_trec_runs,
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

__version__ = "0.8.0"

__all__ = [
    "AggregateRankingMetrics",
    "CANDIDATE_GREATER_ALTERNATIVE",
    "CANDIDATE_LESS_ALTERNATIVE",
    "CONVEX_COMBINATION_STRATEGY",
    "COSINE_DISTANCE_THEORETICAL_BOUNDS",
    "DEFAULT_MAX_QUERY_CHARACTER_LENGTH",
    "DEFAULT_RANDOMIZATION_COUNT",
    "DEFAULT_RANDOM_SEED",
    "EXACT_RANDOMIZATION_METHOD",
    "EXACT_RANDOMIZATION_PAIR_LIMIT",
    "FusedRankedItem",
    "FusedScoredItem",
    "FusedWeightedRankedItem",
    "FusionSettings",
    "MEAN_NDCG_OBJECTIVE",
    "MEAN_PRECISION_OBJECTIVE",
    "MEAN_RECALL_OBJECTIVE",
    "MEAN_RECIPROCAL_RANK_OBJECTIVE",
    "MONTE_CARLO_RANDOMIZATION_METHOD",
    "NDCG_AT_K_METRIC",
    "PRECISION_AT_K_METRIC",
    "PairedRandomizationResult",
    "QueryMetricDifference",
    "QueryRankingMetrics",
    "RECALL_AT_K_METRIC",
    "RECIPROCAL_RANK_AT_K_METRIC",
    "RECIPROCAL_RANK_STRATEGY",
    "RankingComparisonReport",
    "RankingEvaluationReport",
    "RankingMetrics",
    "SUPPORTED_COMPARISON_ALTERNATIVES",
    "SUPPORTED_COMPARISON_METRICS",
    "SUPPORTED_TUNING_OBJECTIVES",
    "TWO_SIDED_ALTERNATIVE",
    "TrecQrelEntry",
    "TrecQrels",
    "TrecRun",
    "TrecRunComparisonReport",
    "TrecRunEntry",
    "WORD_SIMILARITY_THEORETICAL_BOUNDS",
    "WeightedChannelContribution",
    "WeightedRRFTuningReport",
    "WeightedRRFTuningTrial",
    "WeightedRankContribution",
    "compare_ranking_reports",
    "compare_rankings",
    "compare_trec_runs",
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
