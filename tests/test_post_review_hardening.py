# Post-merge review regressions for the autonomous trust boundary.

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github/workflows/hourly-commercialization-loop.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_agent_control_policy_is_not_autonomously_editable():
    workflow = _workflow_text()
    implementation_permissions = workflow[
        workflow.index("      - name: Configure implementation permissions") :
        workflow.index("      - name: Implement the bounded product increment")
    ]
    diff_gate = workflow[
        workflow.index("      - name: Enforce the autonomous diff boundary") :
        workflow.index("      - name: Record the pre-validation workspace manifest")
    ]

    assert '"AGENTS.md": "deny"' in implementation_permissions
    assert '"AGENTS.md"' in diff_gate[diff_gate.index("forbidden_exact") :]
    allowed_exact = diff_gate[
        diff_gate.index("allowed_exact") : diff_gate.index("allowed_prefixes")
    ]
    assert '"AGENTS.md"' not in allowed_exact
    assert "Update CHANGELOG.md, README.md, AGENTS.md" not in workflow


def test_queue_and_exact_base_are_rechecked_before_oidc_token_exchange():
    workflow = _workflow_text()
    preflight_index = workflow.index("Recheck queue and base before token exchange")
    exchange_index = workflow.index(
        "Exchange an OpenCode app token for generated PR events"
    )
    mutation_index = workflow.index("Open exactly one focused pull request")

    assert preflight_index < exchange_index < mutation_index
    preflight = workflow[preflight_index:exchange_index]
    assert "/pulls?state=open&per_page=1" in preflight
    assert "/commits/${BASE_BRANCH}" in preflight
    exchange = workflow[exchange_index:mutation_index]
    assert "steps.mutation_preflight.outputs.eligible == 'true'" in exchange
    mutation = workflow[mutation_index:]
    assert "steps.mutation_preflight.outputs.eligible == 'true'" in mutation
