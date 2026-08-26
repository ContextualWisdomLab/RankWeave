"""Enforce ADR 0005: the public API surface frozen at rankweave 0.18.0 stays exported.

See docs/adr/0005-public-api-compatibility-policy.md. A name in this frozen
set is not removed or renamed within a minor version; removing one requires
updating this file, CHANGELOG.md's ``### Removed`` section, and the ADR in
the same reviewed change. Adding new public names does not require touching
this file — the assertion is a lower bound, not an exact match.
"""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

import rankweave

FROZEN_PUBLIC_API_AT_0_18_0 = {
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
    "theoretical_min_max_normalize",
    "tune_weighted_convex_fusion",
    "tune_weighted_reciprocal_rank_fusion",
    "verify_report_artifacts",
    "weighted_convex_combination_score",
    "weighted_convex_fuse",
    "weighted_reciprocal_rank_fuse",
    "weighted_reciprocal_rank_fusion_score",
}


def test_frozen_0_18_0_public_api_remains_exported():
    """No frozen 0.18.0 name disappears from ``__all__`` within this minor version."""
    assert FROZEN_PUBLIC_API_AT_0_18_0 <= set(rankweave.__all__)


def test_frozen_0_18_0_public_api_remains_resolvable():
    """No name frozen at 0.18.0 becomes unimportable within this minor version."""
    for symbol_name in FROZEN_PUBLIC_API_AT_0_18_0:
        assert hasattr(rankweave, symbol_name), symbol_name


def test_frozen_cli_entrypoint_remains_installed():
    """ADR 0005 keeps the documented console command mapped to its adapter."""

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["rankweave"] == "rankweave.cli:main"


def test_frozen_cli_transport_versions_remain_available():
    """ADR 0005 keeps both established JSON transport versions discoverable."""

    descriptors = rankweave.available_report_schemas()
    versions = {descriptor.transport_schema_id for descriptor in descriptors}
    assert {
        "rankweave.artifact-verification.v1",
        "rankweave.trec-comparison.v1",
        "rankweave.trec-comparison.v2",
        "rankweave.trec-family-comparison.v1",
        "rankweave.trec-family-comparison.v2",
    } <= versions
