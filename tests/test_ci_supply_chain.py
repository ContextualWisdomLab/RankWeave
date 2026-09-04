import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = PROJECT_ROOT / ".github/workflows/ci.yml"
FULL_SHA_REFERENCE = re.compile(
    r"uses:\s+([^\s@]+)@([0-9a-f]{40})(?:\s|$)"
)

CHECKOUT_SHA = "de0fac2e4500dabe0009e67214ff5f5447ce83dd"
SETUP_PYTHON_SHA = "a309ff8b426b58ec0e2a45f0f869d46889d02405"
SETUP_UV_SHA = "08807647e7069bb48b6ef5acd8ec9567f424441b"
SUPERSEDED_SHAS = {
    "11d5960a326750d5838078e36cf38b85af677262",
    "a26af69be951a213d495a4c3e4e4022e16d87065",
    "c771a70e6277c0a99b617c7a806ffedaca235ff9",
}


def _workflow_text() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_ci_concurrency_only_cancels_superseded_pull_request_heads():
    workflow = _workflow_text()

    assert "${{ github.workflow }}-${{ github.repository }}-${{" in workflow
    assert "github.event.pull_request.number || github.run_id" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow


def test_ci_only_admits_ready_open_pull_requests():
    workflow = _workflow_text()

    assert "ready_for_review, converted_to_draft, closed" in workflow
    assert workflow.count("github.event.pull_request.draft == false") == 2
    assert workflow.count("github.event.action != 'closed'") == 2


def _references(workflow: str) -> tuple[tuple[str, str], ...]:
    return tuple(FULL_SHA_REFERENCE.findall(workflow))


def test_ci_pins_reviewed_node24_action_commits():
    workflow = _workflow_text()

    assert workflow.count(f"actions/checkout@{CHECKOUT_SHA}") == 2
    assert workflow.count(f"actions/setup-python@{SETUP_PYTHON_SHA}") == 2
    assert workflow.count(f"astral-sh/setup-uv@{SETUP_UV_SHA}") == 2

    expected = {
        ("actions/checkout", CHECKOUT_SHA),
        ("actions/setup-python", SETUP_PYTHON_SHA),
        ("astral-sh/setup-uv", SETUP_UV_SHA),
    }
    assert expected <= set(_references(workflow))


def test_ci_rejects_superseded_action_commits():
    workflow = _workflow_text()

    for superseded_sha in SUPERSEDED_SHAS:
        assert superseded_sha not in workflow
