import rankweave


def test_package_root_exports_direct_trec_comparison_api():
    exported_symbols = {
        "TrecRunComparisonReport",
        "compare_trec_runs",
    }

    assert exported_symbols <= set(rankweave.__all__)
    for symbol_name in exported_symbols:
        assert hasattr(rankweave, symbol_name)
