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


def test_product_development_uses_nvidia_nim_and_fails_closed():
    workflow = _workflow_text()

    assert "NVIDIA_NIM_API_KEY" in workflow
    assert "COPILOT_GITHUB_TOKEN" not in workflow
    assert "/agents/repos" not in workflow
    assert workflow.count("/pulls?state=open&per_page=1") == 2
    assert (
        "NVIDIA_NIM_API_KEY is not configured; product development remains "
        "fail-closed" in workflow
    )
    assert '"enabled_providers": ["nvidia"]' in workflow
    assert "@ai-sdk/openai-compatible" not in workflow
    assert "integrate.api.nvidia.com" not in workflow


def test_nvidia_secret_is_step_scoped_and_agent_has_no_github_credential():
    workflow = _workflow_text()
    develop = workflow[workflow.index("  develop-next-product-gap:\n") :]
    job_environment = develop.split("    steps:\n", maxsplit=1)[0]

    assert "NVIDIA_API_KEY" not in job_environment
    assert workflow.count("NVIDIA_API_KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}") == 3
    assert "persist-credentials: false" in workflow
    assert workflow.count("env -u GH_TOKEN -u GITHUB_TOKEN") == 2
    assert workflow.count("-u ACTIONS_ID_TOKEN_REQUEST_TOKEN") == 2
    assert "GH_TOKEN: ${{ github.token }}" not in workflow[
        workflow.index("Author one design and failing regression test") :
        workflow.index("Enforce the autonomous diff boundary")
    ]


def test_opencode_permissions_block_execution_network_and_protected_edits():
    workflow = _workflow_text()

    for denied_permission in (
        '"bash": "deny"',
        '"webfetch": "deny"',
        '"websearch": "deny"',
        '"external_directory": "deny"',
        '"task": "deny"',
        '"skill": "deny"',
        '"question": "deny"',
        '"lsp": "deny"',
    ):
        assert workflow.count(denied_permission) == 2
    assert '"tests/**": "allow"' in workflow
    assert '"docs/superpowers/specs/**": "allow"' in workflow
    assert '".github/**": "deny"' in workflow
    assert '".git/**": "deny"' in workflow
    assert "Do not read GitHub issues, pull requests, external web pages" in workflow


def test_product_development_proves_a_red_state_before_implementation():
    workflow = _workflow_text()

    assert "Author one design and failing regression test" in workflow
    assert "red phase may not rename, copy, or delete files" in workflow
    assert "red phase did not add or modify a pytest file" in workflow
    assert "Expected pytest exit 1 from a genuine red test" in workflow
    assert 'grep -q "FAILED"' in workflow
    assert "AUTOMATION_RED_SHA=$(git rev-parse HEAD)" in workflow
    assert "restoring the verified red state" in workflow


def test_product_prompt_enforces_bounded_commercial_quality():
    workflow = _workflow_text()

    required_phrases = (
        "exactly one highest-impact buyer-visible product gap",
        "write the failing",
        "full production docstrings",
        "standard-library-only runtime",
        "Update CHANGELOG.md",
        "Do not commit, push",
        "Figma is not applicable because RankWeave has no UI",
        "exactly one focused pull request",
    )
    for required_phrase in required_phrases:
        assert required_phrase in workflow
    assert "python -m coverage report" in workflow


def test_autonomous_diff_is_text_only_bounded_and_policy_safe():
    workflow = _workflow_text()

    for variable in (
        "MAX_AUTONOMOUS_CHANGED_FILES",
        "MAX_AUTONOMOUS_FILE_BYTES",
        "MAX_AUTONOMOUS_TOTAL_BYTES",
    ):
        assert variable in workflow
    for protected_path in (
        '".gitmodules"',
        '"CODEOWNERS"',
        '"SECURITY.md"',
        '".github/"',
        '".git/"',
    ):
        assert protected_path in workflow
    assert "non-regular file changed" in workflow
    assert "NUL byte found" in workflow
    assert "non-text or unsupported path changed" in workflow
    assert "must change a production Python module" in workflow


def test_untrusted_validation_has_no_network_or_inherited_environment():
    workflow = _workflow_text()

    assert workflow.count("sudo unshare --net --pid --fork --mount-proc") == 3
    assert workflow.count("env -i") == 2
    assert "PIP_NO_INDEX=1" in workflow
    assert "workspace-manifest-before.json" in workflow
    assert "validation mutated the proposed working tree" in workflow
    assert "--no-build-isolation" in workflow
    assert "--no-index" in workflow
    assert "python -m ruff check ." in workflow
    assert "python -m coverage run -m pytest -q" in workflow
    assert "python -m coverage report" in workflow
    assert "python -m pip wheel" in workflow
    assert "-m pip check" in workflow


def test_final_queue_and_base_are_rechecked_before_pr_creation():
    workflow = _workflow_text()

    assert workflow.count("/pulls?state=open&per_page=1") == 2
    assert "/commits/${BASE_BRANCH}" in workflow
    assert "The base branch moved during authoring" in workflow
    assert "Another pull request acquired the queue" in workflow
    assert "git reset --soft \"$AUTOMATION_BASE_SHA\"" in workflow
    assert "core.hooksPath=/dev/null" in workflow
    assert "gh pr create" in workflow
    assert "gh pr merge" not in workflow


def test_product_development_requires_successful_pr_governance():
    workflow = _workflow_text()

    assert (
        "needs: [inspect-pr-queue, repair-review-feedback, revalidate-pr-queue]"
        in workflow
    )
    assert "needs.inspect-pr-queue.result == 'success'" in workflow
    assert "needs.repair-review-feedback.result == 'success'" in workflow
    assert "needs.revalidate-pr-queue.result == 'success'" in workflow


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


def test_opencode_binary_and_models_are_pinned():
    workflow = _workflow_text()

    assert 'OPENCODE_VERSION: "1.17.13"' in workflow
    assert "OPENCODE_SHA256:" in workflow
    assert "sha256sum -c -" in workflow
    for model in (
        "nvidia/nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "nvidia/nvidia/nemotron-3-super-120b-a12b",
        "nvidia/deepseek-ai/deepseek-v4-pro",
    ):
        assert model in workflow


def test_untrusted_execution_drops_privileges():
    workflow = _workflow_text()

    assert 'venv="/tmp/rankweave-automation-venv-${GITHUB_RUN_ID}"' in workflow
    assert 'sudo chown -R root:root "$venv"' in workflow
    assert 'sudo chmod -R a-w "$venv"' in workflow
    assert workflow.count("            setpriv\n") == 3
    assert workflow.count('--reuid="$SANDBOX_UID"') == 3
    assert workflow.count('--regid="$SANDBOX_GID"') == 3
    assert workflow.count("--no-new-privs") == 3
    assert workflow.count("--bounding-set=-all") == 3
    assert workflow.count("PYTHONPATH=$GITHUB_WORKSPACE/src") == 2
    assert 'pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"' in workflow
    assert "/usr/bin/python3 -I -S - <<'PY'" in workflow
    assert "strict UTF-8" in workflow

