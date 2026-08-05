from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = PROJECT_ROOT / ".github/workflows/ci.yml"
PUBLISH_WORKFLOW = PROJECT_ROOT / ".github/workflows/publish.yml"
TEMPORAL_MODULE = "rankweave/temporal_backtesting.py"
RELEASE_VERSION = "0.18.0"


def test_package_and_release_workflows_require_temporal_module():
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    publish_workflow = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert ci_workflow.count(TEMPORAL_MODULE) == 1
    assert publish_workflow.count(TEMPORAL_MODULE) == 1


def test_installed_package_smoke_targets_current_temporal_release():
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert ci_workflow.count(f'== "{RELEASE_VERSION}"') >= 2
    assert "backtest_weighted_convex_fusion" in ci_workflow
    assert "WeightedConvexBacktestWindowDefinition" in ci_workflow
    assert "WeightedConvexBacktestReport" in ci_workflow
    assert "WeightedConvexBacktestWindow" in ci_workflow
