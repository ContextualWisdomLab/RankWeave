"""Apply the reviewed PR 24 hardening and remove bootstrap files."""

from __future__ import annotations

from pathlib import Path

HOURLY_WORKFLOW = Path(".github/workflows/hourly-commercialization-loop.yml")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
TEMPORARY_WORKFLOW = Path(".github/workflows/patch-post-review-hardening.yml")
THIS_SCRIPT = Path(".github/scripts/apply_pr24_post_review.py")
REPAIR_JOB_MARKER = "\n  repair-post-review:\n"


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace one reviewed fragment and fail closed on source drift."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one fragment, found {count}")
    return text.replace(old, new, 1)


def _patch_hourly_workflow() -> None:
    """Protect agent controls and add a pre-token mutation preflight."""
    workflow = HOURLY_WORKFLOW.read_text(encoding="utf-8")
    workflow = _replace_once(
        workflow,
        '''              "edit": {
                "*": "allow",
                ".github/**": "deny",
''',
        '''              "edit": {
                "*": "allow",
                "AGENTS.md": "deny",
                ".github/**": "deny",
''',
        label="implementation agent-control permission",
    )
    workflow = _replace_once(
        workflow,
        "          Update CHANGELOG.md, README.md, AGENTS.md, relevant product or operations\n",
        "          Update CHANGELOG.md, README.md, relevant product or operations\n",
        label="implementation documentation prompt",
    )
    workflow = _replace_once(
        workflow,
        '          forbidden_exact = {".gitmodules", "CODEOWNERS", "SECURITY.md"}\n',
        '''          forbidden_exact = {
              ".gitmodules",
              "AGENTS.md",
              "CODEOWNERS",
              "SECURITY.md",
          }
''',
        label="autonomous protected exact paths",
    )
    workflow = _replace_once(
        workflow,
        '''          allowed_exact = {
              "AGENTS.md",
              "CHANGELOG.md",
''',
        '''          allowed_exact = {
              "CHANGELOG.md",
''',
        label="autonomous exact allowlist",
    )

    token_step = '''      - name: Exchange an OpenCode app token for generated PR events
        id: generated_pr_token
        if: steps.gate.outputs.eligible == 'true'
'''
    preflight_and_token = '''      - name: Recheck queue and base before token exchange
        id: mutation_preflight
        if: steps.gate.outputs.eligible == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          open_pr_count="$(
            gh api "/repos/${TARGET_REPOSITORY}/pulls?state=open&per_page=1" \\
              --jq 'length'
          )"
          if [ "$open_pr_count" -ne 0 ]; then
            echo "Another pull request acquired the queue before token exchange."
            echo "eligible=false" >>"$GITHUB_OUTPUT"
            exit 0
          fi

          current_base_sha="$(
            gh api "/repos/${TARGET_REPOSITORY}/commits/${BASE_BRANCH}" \\
              --jq '.sha'
          )"
          if [ "$current_base_sha" != "$AUTOMATION_BASE_SHA" ]; then
            echo "The base branch moved before token exchange."
            echo "eligible=false" >>"$GITHUB_OUTPUT"
            exit 0
          fi

          echo "eligible=true" >>"$GITHUB_OUTPUT"

      - name: Exchange an OpenCode app token for generated PR events
        id: generated_pr_token
        if: steps.mutation_preflight.outputs.eligible == 'true'
'''
    workflow = _replace_once(
        workflow,
        token_step,
        preflight_and_token,
        label="generated PR token preflight",
    )
    workflow = _replace_once(
        workflow,
        '''      - name: Open exactly one focused pull request
        if: steps.gate.outputs.eligible == 'true'
''',
        '''      - name: Open exactly one focused pull request
        if: steps.mutation_preflight.outputs.eligible == 'true'
''',
        label="generated PR mutation condition",
    )
    HOURLY_WORKFLOW.write_text(workflow, encoding="utf-8")


def _remove_repair_job() -> None:
    """Restore the normal CI workflow after this one-shot job starts."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    if workflow.count(REPAIR_JOB_MARKER) != 1:
        raise RuntimeError("one-shot CI repair marker is missing or duplicated")
    CI_WORKFLOW.write_text(
        workflow.split(REPAIR_JOB_MARKER, 1)[0].rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Apply hardening, remove bootstrap files, and return success."""
    _patch_hourly_workflow()
    _remove_repair_job()
    TEMPORARY_WORKFLOW.unlink(missing_ok=True)
    THIS_SCRIPT.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
