from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github/workflows/hourly-commercialization-loop.yml"
MERGE_WORKFLOW_SHA = "5983b41ace75040c1d81818171ca7d0f3653254e"
FIX_WORKFLOW_SHA = "21397126d708d2d536ccc1d68b0d333653ce9315"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _job_section(workflow: str, job_name: str, next_job_name: str) -> str:
    start = workflow.index(f"  {job_name}:\n")
    end = workflow.index(f"  {next_job_name}:\n", start)
    return workflow[start:end]


def test_commercialization_loop_runs_once_each_hour():
    workflow = _workflow_text()

    assert 'cron: "17 * * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "cancel-in-progress: true" in workflow


def test_commercialization_loop_uses_pinned_central_pr_governance():
    workflow = _workflow_text()

    merge_reference = (
        "ContextualWisdomLab/.github/.github/workflows/"
        f"pr-review-merge-scheduler.yml@{MERGE_WORKFLOW_SHA}"
    )
    fix_reference = (
        "ContextualWisdomLab/.github/.github/workflows/"
        f"pr-review-fix-scheduler.yml@{FIX_WORKFLOW_SHA}"
    )
    assert workflow.count(merge_reference) == 2
    assert workflow.count(fix_reference) == 1
    assert 'retry_hours: "1"' in workflow
    assert "secrets: inherit" in workflow


def test_product_development_is_single_flight_and_fails_closed():
    workflow = _workflow_text()

    assert "COPILOT_GITHUB_TOKEN" in workflow
    assert "secrets.COPILOT_GITHUB_TOKEN || github.token" not in workflow
    assert "/pulls?state=open&per_page=1" in workflow
    assert "/agents/repos/${TARGET_REPOSITORY}/tasks" in workflow
    assert '"queued", "in_progress", "idle", "waiting_for_user"' in workflow
    assert "Unable to list Copilot agent tasks; refusing to create another" in workflow
    assert "create_pull_request: true" in workflow


def test_product_prompt_enforces_bounded_commercial_quality():
    workflow = _workflow_text()

    required_phrases = (
        "exactly one highest-impact buyer-visible product gap",
        "Write a failing test before production code",
        "100% line and branch coverage",
        "complete production docstrings",
        "standard-library-only runtime",
        "Update CHANGELOG.md",
        "Do not merge your own pull request",
        "Figma or Product Design only when the repository has an actual UI",
    )
    for required_phrase in required_phrases:
        assert required_phrase in workflow


def test_product_development_requires_successful_pr_governance():
    workflow = _workflow_text()

    assert (
        "needs: [inspect-pr-queue, repair-review-feedback, revalidate-pr-queue]"
        in workflow
    )
    assert "needs.inspect-pr-queue.result == 'success'" in workflow
    assert "needs.repair-review-feedback.result == 'success'" in workflow
    assert "needs.revalidate-pr-queue.result == 'success'" in workflow


def test_agent_task_inventory_is_paginated():
    workflow = _workflow_text()

    assert "--paginate" in workflow
    assert "--slurp" in workflow
    assert "per_page=100" in workflow


def test_governance_permissions_are_scoped_per_calling_job():
    workflow = _workflow_text()
    workflow_default = workflow.split("concurrency:", maxsplit=1)[0]
    inspect = _job_section(workflow, "inspect-pr-queue", "repair-review-feedback")
    repair = _job_section(workflow, "repair-review-feedback", "revalidate-pr-queue")
    revalidate = _job_section(
        workflow, "revalidate-pr-queue", "develop-next-product-gap"
    )

    assert "permissions:\n  contents: read" in workflow_default
    for forbidden_permission in (
        "actions: write",
        "contents: write",
        "id-token: write",
        "issues: write",
        "pull-requests: write",
    ):
        assert forbidden_permission not in workflow_default

    for merge_job in (inspect, revalidate):
        for permission in (
            "actions: write",
            "checks: read",
            "contents: write",
            "id-token: write",
            "pull-requests: write",
        ):
            assert permission in merge_job
        assert "issues: write" not in merge_job
        assert "statuses: read" not in merge_job

    for permission in (
        "actions: write",
        "contents: read",
        "issues: write",
        "pull-requests: read",
        "statuses: read",
    ):
        assert permission in repair
    assert "contents: write" not in repair
    assert "id-token: write" not in repair


def test_agent_tasks_use_current_public_preview_api_version():
    workflow = _workflow_text()

    assert workflow.count("X-GitHub-Api-Version: 2026-03-10") == 2
    assert "X-GitHub-Api-Version: 2022-11-28" not in workflow
