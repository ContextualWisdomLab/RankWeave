"""Keep repository-owned pull-request CI on an explicit hosted-runner image."""

from pathlib import Path

CI_WORKFLOW = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
)


def test_ci_uses_explicit_ubuntu_2404() -> None:
    """Reject the floating alias that has repeatedly stalled before checkout."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" not in workflow
    assert workflow.count("runs-on: ubuntu-24.04") == 2
