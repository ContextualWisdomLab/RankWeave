from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = PROJECT_ROOT / ".github/workflows/ci.yml"
CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"


def test_ci_pins_checkout_to_reviewed_commit_sha():
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count(f"actions/checkout@{CHECKOUT_SHA}") == 2
    assert "actions/checkout@11d5960a32675040c1d81818171ca7d0f3653254e" not in workflow
