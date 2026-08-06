"""Apply the reviewed fail-closed repair for the hourly commercialization loop."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path_text: str) -> str:
    """Read one repository text file as UTF-8."""
    return (ROOT / path_text).read_text(encoding="utf-8")


def write(path_text: str, content: str) -> None:
    """Write one repository text file as UTF-8."""
    path = ROOT / path_text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def replace_exact(path_text: str, old: str, new: str) -> None:
    """Replace one exact block or fail on an unexpected source tree."""
    content = read(path_text)
    if content.count(old) != 1:
        raise SystemExit(
            f"{path_text}: expected exactly one reviewed replacement block"
        )
    write(path_text, content.replace(old, new, 1))


def insert_after(path_text: str, marker: str, addition: str) -> None:
    """Insert one idempotent block after an exact marker."""
    content = read(path_text)
    if addition.strip() in content:
        return
    if content.count(marker) != 1:
        raise SystemExit(f"{path_text}: expected one marker {marker!r}")
    write(path_text, content.replace(marker, marker + addition, 1))


OLD_REPAIR_JOB = """  repair-review-feedback:
    needs: inspect-pr-queue
    if: ${{ always() }}
    permissions:
      actions: write
      contents: read
      issues: write
      pull-requests: read
      statuses: read
    uses: ContextualWisdomLab/.github/.github/workflows/pr-review-fix-scheduler.yml@21397126d708d2d536ccc1d68b0d333653ce9315
    with:
      target_repository: ContextualWisdomLab/RankWeave
      base_branch: main
      max_prs: "50"
      max_dispatches: "1"
      retry_hours: "1"
    secrets: inherit

"""
NEW_REPAIR_JOB = """  repair-review-feedback:
    needs: inspect-pr-queue
    if: ${{ always() }}
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
      pull-requests: read
    env:
      TARGET_REPOSITORY: ContextualWisdomLab/RankWeave
    steps:
      - name: Keep review repair fail-closed until protected NVIDIA repair is available
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          open_pr_count="$(
            gh api "/repos/${TARGET_REPOSITORY}/pulls?state=open&per_page=1" \\
              --jq 'length'
          )"
          if [ "$open_pr_count" -eq 0 ]; then
            echo "No pull request requires review repair."
            exit 0
          fi
          echo "::notice::Review repair remains fail-closed while the protected central NVIDIA NIM scheduler is pending. Existing independent review agents and the central merge scheduler remain unchanged."

"""
replace_exact(
    ".github/workflows/hourly-commercialization-loop.yml",
    OLD_REPAIR_JOB,
    NEW_REPAIR_JOB,
)

TEST_CONSTANT = (
    'FIX_WORKFLOW_SHA = "21397126d708d2d536ccc1d68b0d333653ce9315"\n'
)
replace_exact("tests/test_hourly_commercialization_workflow.py", TEST_CONSTANT, "")

OLD_TEST = """def test_commercialization_loop_uses_pinned_central_pr_governance():
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


"""
NEW_TEST = """def test_commercialization_loop_uses_reachable_merge_governance():
    workflow = _workflow_text()

    merge_reference = (
        "ContextualWisdomLab/.github/.github/workflows/"
        f"pr-review-merge-scheduler.yml@{MERGE_WORKFLOW_SHA}"
    )
    assert workflow.count(merge_reference) == 2
    assert "pr-review-fix-scheduler.yml@" not in workflow
    assert workflow.count("secrets: inherit") == 2


def test_review_repair_bridge_is_local_read_only_and_provider_neutral():
    workflow = _workflow_text()
    repair = _job_section(
        workflow,
        "repair-review-feedback",
        "revalidate-pr-queue",
    )

    assert "runs-on: ubuntu-latest" in repair
    assert "contents: read" in repair
    assert "pull-requests: read" in repair
    for forbidden in (
        "actions: write",
        "contents: write",
        "id-token: write",
        "issues: write",
        "statuses: read",
        "secrets: inherit",
        "github-models/",
        "STRIX_GITHUB_MODELS_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "NVIDIA_NIM_API_KEY",
    ):
        assert forbidden not in repair
    assert "protected central NVIDIA NIM scheduler is pending" in repair
    assert "/pulls?state=open&per_page=1" in repair


"""
replace_exact("tests/test_hourly_commercialization_workflow.py", OLD_TEST, NEW_TEST)

OLD_SEQUENCE = """2. **Repair review feedback.** Call the central review-fix scheduler with one
   dispatch of budget and a one-hour same-head retry interval.
"""
NEW_SEQUENCE = """2. **Hold repair fail-closed when the protected repair engine is unavailable.**
   Inspect the open-PR queue without a mutation credential. Until the protected
   central NVIDIA NIM repair scheduler is merged, do not call an orphaned or
   GitHub-Models-backed repair ref; independent review agents and the merge
   scheduler continue to operate normally.
"""
replace_exact(
    "docs/operations/hourly-commercialization-loop.md",
    OLD_SEQUENCE,
    NEW_SEQUENCE,
)

OLD_REFS = """- merge/revalidation policy:
  `5983b41ace75040c1d81818171ca7d0f3653254e`;
- hourly review-repair policy with called-workflow source bound to
  `job.workflow_repository` and `job.workflow_sha`:
  `21397126d708d2d536ccc1d68b0d333653ce9315`.

This prevents a privileged scheduled run from silently changing behavior
because the central `main` branch moved. Updating either central policy
requires an explicit reviewed SHA change in RankWeave.
"""
NEW_REFS = """- merge/revalidation policy:
  `5983b41ace75040c1d81818171ca7d0f3653254e`.

The former review-repair SHA, `21397126d708d2d536ccc1d68b0d333653ce9315`,
was no longer reachable from the protected central history. GitHub rejected the
caller before creating any jobs, so every scheduled run failed without doing PR
maintenance or product development. RankWeave now uses a local read-only hold
job until the protected central NVIDIA NIM repair scheduler is available. This
keeps the hourly workflow executable without routing repairs through GitHub
Models, a mutable branch, or an unmerged central change.

Updating the central merge policy or re-enabling review repair requires an
explicit reviewed reachable SHA change in RankWeave.
"""
replace_exact(
    "docs/operations/hourly-commercialization-loop.md",
    OLD_REFS,
    NEW_REFS,
)

INCIDENT_SECTION = """## Reusable-workflow reachability incident

GitHub Actions run `31124811165` and its immediate predecessors failed before
job creation. The caller still pinned the review-fix workflow to commit
`21397126d708d2d536ccc1d68b0d333653ce9315`, which had diverged from the
protected central history. The same caller had last succeeded before that
central ref became unreachable.

The repair is deliberately narrower than copying the central engine into this
repository. The local bridge is read-only and does not invoke a model or mutate
a PR. Once the protected central scheduler provides the reviewed NVIDIA NIM
boundary, RankWeave can replace the bridge with a new immutable reachable SHA.
This preserves the standalone repository, the central MSA control plane, and
the existing independent-review credential system.

"""
insert_after(
    "docs/operations/hourly-commercialization-loop.md",
    "## Product-development trust zones\n\n",
    INCIDENT_SECTION,
)

CHANGELOG_ENTRY = """### Fixed
- Replaced an unreachable central review-fix reusable-workflow SHA that caused
  scheduled commercialization runs to fail before job creation with a local
  read-only, provider-neutral hold job.
- Kept review repair fail-closed until the protected central NVIDIA NIM/OpenCode
  scheduler is merged, without falling back to GitHub Models,
  `COPILOT_GITHUB_TOKEN`, inherited repair secrets, or mutable central code.
- Preserved hourly PR inspection, exact-policy revalidation, and the existing
  NVIDIA NIM product-development stage while preventing a single unavailable
  repair engine from disabling the entire loop.

"""
insert_after("CHANGELOG.md", "## [Unreleased]\n\n", CHANGELOG_ENTRY)

DOCTORING = """# Hourly reusable-workflow reachability incident

- **Date:** 2026-08-07
- **Component:** `.github/workflows/hourly-commercialization-loop.yml`
- **Failure:** scheduled workflow concluded `failure` before GitHub created any
  jobs.

## Root cause

RankWeave pinned the central review-fix reusable workflow to commit
`21397126d708d2d536ccc1d68b0d333653ce9315`. That commit later diverged from the
protected central history, so the caller could no longer resolve the reusable
workflow. Recent failed runs contained zero jobs, while the last successful
hourly run used the same RankWeave caller before the central ref became
unreachable.

## Remediation

The local hourly workflow now retains its reachable immutable merge-scheduler
calls and replaces the unavailable repair call with a read-only local hold job.
The bridge checks whether an open PR exists and records the fail-closed repair
state, but it has no write, OIDC, issue, provider, or model credential. It does
not copy the repair engine and does not fall back to GitHub Models.

The central repair call may return only after a protected central NVIDIA
NIM/OpenCode scheduler has merged and RankWeave pins its reachable immutable
commit. The existing independent review workflows and their credentials remain
unchanged.

## Verification

- Contract tests reject any `pr-review-fix-scheduler.yml@...` reference in the
  temporary bridge state.
- Contract tests require two immutable merge-scheduler calls.
- Contract tests require the bridge to remain local, read-only, secret-free,
  provider-neutral, and bounded.
- Full Python 3.10-3.13 CI, package smoke, Security Scan, and SAST must pass on
  the exact PR head before merge.

## Rollback

Restore a central review-repair call only with a protected, reachable, reviewed
commit SHA whose workflow uses NVIDIA NIM/OpenCode and preserves the existing
review-agent credential boundary. Never restore the orphaned SHA or substitute
a mutable branch.

## References

GitHub. (2026). *Reusing workflow configurations*. GitHub Docs.
https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

GitHub. (2026). *GITHUB_TOKEN*. GitHub Docs.
https://docs.github.com/en/actions/concepts/security/github_token
"""
write(
    "docs/doctoring/hourly-reusable-workflow-reachability.md",
    DOCTORING,
)

ADR = """# ADR 0006: Fail closed when the central repair workflow is unreachable

- **Status:** Accepted
- **Date:** 2026-08-07

## Context

The hourly RankWeave workflow composed central inspection, review repair,
revalidation, and local NVIDIA NIM product development. Its review-repair call
was pinned to a central commit that became unreachable from protected central
history. GitHub rejected each scheduled caller before creating jobs, disabling
the whole loop.

The current protected central repair implementation still uses GitHub Models,
while a reviewed NVIDIA NIM replacement remains outside protected main. Calling
either the orphaned SHA, mutable central `main`, or an unmerged branch would
violate the product's credential and immutable-source boundaries.

## Decision

Keep the two immutable reachable merge-scheduler calls. Replace review repair
with a local read-only hold job until the protected central NVIDIA NIM repair
engine is available at a reachable immutable SHA. The hold job may inspect only
the open-PR count and must not receive mutation, OIDC, provider, or inherited
secret permissions.

## Consequences

- The hourly workflow executes instead of failing during reusable-workflow
  resolution.
- PR inspection and revalidation continue each hour.
- Product development can proceed when all governance jobs succeed and the PR
  queue is empty.
- Review repair remains unavailable rather than silently routing through an
  unapproved provider or mutable control plane.
- Re-enabling repair requires a focused PR that pins the protected central
  NVIDIA scheduler and updates tests, operations documentation, and this ADR's
  supersession record.

## Diagram

```mermaid
flowchart LR
    S[Hourly schedule] --> I[Immutable central inspection]
    I --> H[Local read-only repair hold]
    H --> R[Immutable central revalidation]
    R -->|PR queue empty| N[NVIDIA NIM product development]
    R -->|PR open| Q[Ordinary review and checks]
    C[Protected central NVIDIA repair] -. future reachable SHA .-> H
```
"""
write(
    "docs/adr/0006-fail-closed-hourly-repair-bridge.md",
    ADR,
)
