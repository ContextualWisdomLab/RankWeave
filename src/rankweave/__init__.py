"""rankweave — retrieval fusion, evaluation, comparison, and tuning.

Python adapters over one Rust calculation core for lexical, semantic,
learned-sparse, and other retrieval channels, complete-list fusion,
ranked-effectiveness evaluation, paired and family-wise statistical comparison,
offline weight policy tuning, strict TREC interchange, and Unicode NFC query
normalization. Store-agnostic: bring your own channels; rankweave combines and
evaluates their evidence.

Two fusion strategies, research-grounded (see ``docs/research/``):

- ``convex_combination`` (default, "TM2C2") — Bruch et al. (2024): a convex
  combination of theoretically min-max normalized scores; robust,
  distribution-preserving, and requiring no training data. The public API
  supports both the common two-channel pairing and explicit N-channel convex
  weights.
- ``reciprocal_rank_fusion`` — Cormack et al. (2009): the non-parametric
  rank-only alternative, with equal- and convex-weighted complete-list APIs.

Quickstart::

    from rankweave import FusionSettings, fuse_channel_scores

    settings = FusionSettings()  # TM2C2, alpha=0.7
    score = fuse_channel_scores(
        word_similarity_score=0.62,
        cosine_distance=0.30,
        channel_ranks={"lexical": 1, "dense": 1},
        settings=settings,
    )
"""

from rankweave.artifact_verification import (
    FAMILY_REPORT_SCHEMA_VERSION,
    PAIRWISE_REPORT_SCHEMA_VERSION,
    ArtifactVerificationRecord,
    ArtifactVerificationReport,
    verify_report_artifacts,
)
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
from rankweave.cross_validation import (
    WeightedConvexCrossValidationFold,
    WeightedConvexCrossValidationReport,
    WeightedRRFCrossValidationFold,
    WeightedRRFCrossValidationReport,
    cross_validate_weighted_convex_fusion,
    cross_validate_weighted_reciprocal_rank_fusion,
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
from rankweave.report_schemas import (
    ReportSchemaDescriptor,
    available_report_schemas,
    load_report_schema,
    load_report_schema_text,
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
from rankweave.semantic_vector_ranking import (
    SemanticUnitCandidate,
    SemanticUnitRank,
    SemanticUnitRankingReport,
    rank_semantic_units,
    rank_semantic_units_packed,
)
from rankweave.temporal_backtesting import (
    WeightedConvexBacktestReport,
    WeightedConvexBacktestWindow,
    WeightedConvexBacktestWindowDefinition,
    backtest_weighted_convex_fusion,
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
from rankweave.trec_family_comparison import (
    TrecCandidateComparison,
    TrecRunFamilyComparisonReport,
    compare_trec_run_family,
)
from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    MEAN_PRECISION_OBJECTIVE,
    MEAN_RECALL_OBJECTIVE,
    MEAN_RECIPROCAL_RANK_OBJECTIVE,
    SUPPORTED_TUNING_OBJECTIVES,
    WeightedConvexTuningReport,
    WeightedConvexTuningTrial,
    WeightedRRFTuningReport,
    WeightedRRFTuningTrial,
    tune_weighted_convex_fusion,
    tune_weighted_reciprocal_rank_fusion,
)

__version__ = "0.18.0"

__all__ = [
    "AggregateRankingMetrics",
    "ArtifactVerificationRecord",
    "ArtifactVerificationReport",
    "CANDIDATE_GREATER_ALTERNATIVE",
    "CANDIDATE_LESS_ALTERNATIVE",
    "CONVEX_COMBINATION_STRATEGY",
    "COSINE_DISTANCE_THEORETICAL_BOUNDS",
    "DEFAULT_MAX_QUERY_CHARACTER_LENGTH",
    "DEFAULT_RANDOMIZATION_COUNT",
    "DEFAULT_RANDOM_SEED",
    "EXACT_RANDOMIZATION_METHOD",
    "EXACT_RANDOMIZATION_PAIR_LIMIT",
    "FAMILY_REPORT_SCHEMA_VERSION",
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
    "PAIRWISE_REPORT_SCHEMA_VERSION",
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
    "SemanticUnitCandidate",
    "SemanticUnitRank",
    "SemanticUnitRankingReport",
    "ReportSchemaDescriptor",
    "SUPPORTED_COMPARISON_ALTERNATIVES",
    "SUPPORTED_COMPARISON_METRICS",
    "SUPPORTED_TUNING_OBJECTIVES",
    "TWO_SIDED_ALTERNATIVE",
    "TrecCandidateComparison",
    "TrecQrelEntry",
    "TrecQrels",
    "TrecRun",
    "TrecRunComparisonReport",
    "TrecRunEntry",
    "TrecRunFamilyComparisonReport",
    "WORD_SIMILARITY_THEORETICAL_BOUNDS",
    "WeightedChannelContribution",
    "WeightedConvexBacktestReport",
    "WeightedConvexBacktestWindow",
    "WeightedConvexBacktestWindowDefinition",
    "WeightedConvexCrossValidationFold",
    "WeightedConvexCrossValidationReport",
    "WeightedConvexTuningReport",
    "WeightedConvexTuningTrial",
    "WeightedRRFCrossValidationFold",
    "WeightedRRFCrossValidationReport",
    "WeightedRRFTuningReport",
    "WeightedRRFTuningTrial",
    "WeightedRankContribution",
    "available_report_schemas",
    "backtest_weighted_convex_fusion",
    "compare_ranking_reports",
    "compare_rankings",
    "compare_trec_run_family",
    "compare_trec_runs",
    "convex_combination_score",
    "cross_validate_weighted_convex_fusion",
    "cross_validate_weighted_reciprocal_rank_fusion",
    "evaluate_ranking",
    "evaluate_rankings",
    "evaluate_trec_run",
    "format_trec_qrels",
    "format_trec_run",
    "fuse_channel_scores",
    "load_report_schema",
    "load_report_schema_text",
    "normalize_search_text",
    "parse_trec_qrels",
    "parse_trec_run",
    "reciprocal_rank_fuse",
    "reciprocal_rank_fusion_score",
    "rank_semantic_units",
    "rank_semantic_units_packed",
    "theoretical_min_max_normalize",
    "tune_weighted_convex_fusion",
    "tune_weighted_reciprocal_rank_fusion",
    "weighted_convex_combination_score",
    "weighted_convex_fuse",
    "weighted_reciprocal_rank_fuse",
    "verify_report_artifacts",
    "weighted_reciprocal_rank_fusion_score",
    "__version__",
]
