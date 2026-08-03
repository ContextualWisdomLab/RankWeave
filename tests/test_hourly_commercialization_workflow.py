from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github/workflows/hourly-commercialization-loop.yml"
CENTRAL_WORKFLOW_SHA = "5983b41ace75040c1d81818171ca7d0f3653254e"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_commercialization_loop_runs_once_each_hour():
    workflow = _workflow_text()

    assert 'cron: "17 * * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "cancel-in-progress: true" in workflow


def test_commercialization_loop_uses_pinned_central_pr_governance():
    workflow = _workflow_text()

    merge_reference = (
        "ContextualWisdomLab/.github/.github/workflows/"
        f"pr-review-merge-scheduler.yml@{CENTRAL_WORKFLOW_SHA}"
    )
    fix_reference = (
        "ContextualWisdomLab/.github/.github/workflows/"
        f"pr-review-fix-scheduler.yml@{CENTRAL_WORKFLOW_SHA}"
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


def test_caller_grants_central_governance_required_permissions():
    workflow = _workflow_text()

    required_permissions = (
        "actions: write",
        "checks: read",
        "contents: write",
        "id-token: write",
        "issues: write",
        "pull-requests: write",
        "statuses: read",
    )
    for permission in required_permissions:
        assert permission in workflow
