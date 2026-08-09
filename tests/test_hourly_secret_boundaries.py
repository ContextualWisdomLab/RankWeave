from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github/workflows/hourly-commercialization-loop.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _job_section(workflow: str, job_name: str, next_job_name: str) -> str:
    start = workflow.index(f"  {job_name}:\n")
    end = workflow.index(f"  {next_job_name}:\n", start)
    return workflow[start:end]


def _step_section(workflow: str, step_name: str, next_step_name: str) -> str:
    start = workflow.index(f"      - name: {step_name}\n")
    end = workflow.index(f"      - name: {next_step_name}\n", start)
    return workflow[start:end]


def test_merge_governance_does_not_inherit_all_repository_secrets():
    workflow = _workflow_text()
    inspect = _job_section(workflow, "inspect-pr-queue", "repair-review-feedback")
    revalidate = _job_section(
        workflow,
        "revalidate-pr-queue",
        "develop-next-product-gap",
    )

    # The pinned merge scheduler has same-repository GITHUB_TOKEN authority and
    # an OIDC app-token path. RankWeave must not forward every repository secret
    # merely to call that reusable governance workflow.
    assert "secrets: inherit" not in inspect
    assert "secrets: inherit" not in revalidate


def test_nvidia_secret_materialization_follows_the_deterministic_queue_gate():
    workflow = _workflow_text()
    gate = _step_section(
        workflow,
        "Determine whether product development may start",
        "Check out the current base without persisted credentials",
    )
    red_authoring = _step_section(
        workflow,
        "Author one design and failing regression test",
        "Verify test-only scope and observe the red state",
    )

    # An open PR is a deterministic stop and must be decided before any model
    # credential is materialized. NVIDIA credentials belong only to the actual
    # model-backed authoring step after that decision.
    assert "/pulls?state=open&per_page=1" in gate
    assert "NVIDIA_NIM_API_KEY" not in gate
    assert "NVIDIA_API_KEY" not in gate
    assert "NVIDIA_API_KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}" in red_authoring
    assert 'if [ -z "${NVIDIA_API_KEY:-}" ]; then' in red_authoring
