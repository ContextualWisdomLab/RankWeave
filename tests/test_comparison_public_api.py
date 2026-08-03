import rankweave


def test_package_root_exports_paired_comparison_api():
    exported_symbols = {
        "CANDIDATE_GREATER_ALTERNATIVE",
        "CANDIDATE_LESS_ALTERNATIVE",
        "DEFAULT_RANDOMIZATION_COUNT",
        "DEFAULT_RANDOM_SEED",
        "EXACT_RANDOMIZATION_METHOD",
        "EXACT_RANDOMIZATION_PAIR_LIMIT",
        "MONTE_CARLO_RANDOMIZATION_METHOD",
        "NDCG_AT_K_METRIC",
        "PRECISION_AT_K_METRIC",
        "PairedRandomizationResult",
        "QueryMetricDifference",
        "RECALL_AT_K_METRIC",
        "RECIPROCAL_RANK_AT_K_METRIC",
        "RankingComparisonReport",
        "SUPPORTED_COMPARISON_ALTERNATIVES",
        "SUPPORTED_COMPARISON_METRICS",
        "TWO_SIDED_ALTERNATIVE",
        "compare_ranking_reports",
        "compare_rankings",
    }

    assert exported_symbols <= set(rankweave.__all__)
    for symbol_name in exported_symbols:
        assert hasattr(rankweave, symbol_name)
