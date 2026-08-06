# Governed RankWeave Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and execute a least-privilege, fail-closed GitHub Release workflow that publishes the already prepared RankWeave 0.18.0 source tree through the existing PyPI Trusted Publishing pipeline.

**Architecture:** A read-only verification job validates the exact source commit, version identity, release uniqueness, PyPI absence, and complete package quality gate. A protected `contents: write` job creates one stable GitHub Release, and an isolated `actions: write` job explicitly dispatches `publish.yml` with the exact tag and SHA because `GITHUB_TOKEN`-created release events do not start another workflow. `publish.yml` remains the only artifact builder, attestor, and PyPI publisher.

**Tech Stack:** GitHub Actions, Bash, Python 3.13 standard library, `uv==0.11.29`, GitHub CLI, PyPI JSON API, existing RankWeave pytest/Ruff/coverage/build toolchain.

## Global Constraints

- Runtime package remains Python 3.10+ and standard-library-only.
- Workflow actions remain pinned by complete commit SHA.
- Workflow-level permissions are empty; verification receives `contents: read`; release creation receives `contents: write` only.
- No PyPI username, password, API token, `COPILOT_GITHUB_TOKEN`, alternate registry, force tag movement, or `skip-existing` behavior.
- Release tag is exactly `v0.18.0` and targets the exact verified default-branch commit.
- Release is stable, non-draft, and non-prerelease.
- Production statement coverage and branch coverage remain 100%.
- All documentation uses APA 7th references where external authority is cited.

---

### Task 1: Encode the release control-plane contract

**Files:**
- Create: `tests/test_create_release_workflow.py`
- Create: `.github/workflows/create-release.yml`

**Interfaces:**
- Consumes: `pyproject.toml`, `src/rankweave/__init__.py`, `tests/test_version.py`, `CHANGELOG.md`, the existing `pypi` environment, and `.github/workflows/publish.yml`.
- Produces: a `Create RankWeave Release` workflow with manual and bounded bootstrap triggers plus explicit least-privilege publication dispatch.

- [ ] **Step 1: Write contract tests before the workflow exists**

Create tests that load `.github/workflows/create-release.yml` and assert the exact trigger, permissions, full-SHA action pins, version checks, PyPI duplicate check, Git tag and release duplicate checks, quality commands, protected environment, exact target SHA, and forbidden credential fragments.

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/create-release.yml"


def test_release_workflow_has_bounded_bootstrap_and_manual_triggers():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "branches: [main]" in text
    assert "- .github/workflows/create-release.yml" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text


def test_release_workflow_is_fail_closed_and_secretless():
    text = WORKFLOW.read_text(encoding="utf-8")
    for fragment in (
        "PYPI_API_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "password:",
        "skip-existing",
        "skip_existing",
        "--force",
    ):
        assert fragment not in text
    assert "https://pypi.org/pypi/${version}/json" not in text
    assert "https://pypi.org/pypi/rankweave/${version}/json" in text
```

- [ ] **Step 2: Run focused tests and confirm the expected missing-file failure**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest tests/test_create_release_workflow.py -q
```

Expected: failure because `.github/workflows/create-release.yml` is absent.

- [ ] **Step 3: Implement the workflow**

Create a workflow with:

```yaml
name: Create RankWeave Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: Exact package version without the v prefix
        required: true
        type: string
  push:
    branches: [main]
    paths:
      - .github/workflows/create-release.yml

permissions: {}
```

The `verify` job checks out `${{ github.sha }}` with persisted credentials disabled, validates the requested/source version, verifies exact SHA and main ancestry, rejects existing PyPI versions/tags/releases, runs the full quality gate, builds one wheel and one sdist, and extracts deterministic release notes from the matching `CHANGELOG.md` section into an artifact.

The `release` job downloads the notes artifact, uses `environment: pypi`, requests only `contents: write`, rechecks the tag and release absence immediately before mutation, and runs:

```bash
gh release create "v${RELEASE_VERSION}" \
  --repo "$GITHUB_REPOSITORY" \
  --target "$VERIFIED_SHA" \
  --title "RankWeave ${RELEASE_VERSION}" \
  --notes-file release-handoff/RELEASE_NOTES.md
```

- [ ] **Step 4: Run focused tests and workflow lint-sensitive repository checks**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest tests/test_create_release_workflow.py \
  tests/test_publish_workflow.py -q
uv run --frozen --extra dev --python 3.13 python -m ruff check .
```

Expected: all pass.

- [ ] **Step 5: Commit the workflow and contract tests**

```bash
git add .github/workflows/create-release.yml \
  tests/test_create_release_workflow.py
git commit -m "ci: add governed stable release creation"
```

### Task 2: Synchronize release documentation and governance

**Files:**
- Modify: `docs/releasing.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `ARCHITECTURE.md`
- Modify: `CHANGELOG.md`
- Create: `docs/adr/0004-separate-release-authorization-from-publication.md`

**Interfaces:**
- Consumes: the exact workflow contract from Task 1.
- Produces: operator, agent, architecture, and audit guidance describing release authorization separately from artifact publication.

- [ ] **Step 1: Add documentation assertions to the release-workflow test**

```python
def test_release_documentation_records_authorization_and_publication_boundary():
    docs = (ROOT / "docs/releasing.md").read_text(encoding="utf-8")
    assert "create-release.yml" in docs
    assert "release authorization" in docs.lower()
    assert "publish.yml" in docs
    assert "PyPI still exposes only `0.1.0`" in docs
```

- [ ] **Step 2: Run the focused test and observe the documentation failure**

Run the focused test from Task 1. Expected: the new documentation assertion fails.

- [ ] **Step 3: Update durable documentation**

Document:

- public PyPI drift from 0.1.0 to the prepared 0.18.0 source tree;
- `create-release.yml` as the release-authorization plane;
- `publish.yml` as the immutable build/attestation/publication plane;
- exact operator inputs and failure handling;
- the `pypi` environment approval boundary;
- post-publication PyPI and GitHub attestation verification;
- the prohibition on deleting/recreating a published version.

Add ADR 0004 with the rejected alternatives of direct token publishing, combining release creation and publishing in one high-privilege job, mutable-tag publication, and a one-off unreviewed local command.

Add a 0.18.0 `Release operations` bullet to `CHANGELOG.md` because the release tag will include this workflow and documentation.

- [ ] **Step 4: Run focused and complete documentation-sensitive tests**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest tests/test_create_release_workflow.py \
  tests/test_publish_workflow.py tests/test_version.py -q
uv run --frozen --extra dev --python 3.13 python -m ruff check .
```

Expected: all pass.

- [ ] **Step 5: Commit documentation**

```bash
git add docs/releasing.md docs/adr/0004-separate-release-authorization-from-publication.md \
  AGENTS.md CLAUDE.md ARCHITECTURE.md CHANGELOG.md \
  tests/test_create_release_workflow.py
git commit -m "docs: govern release authorization and publication"
```

### Task 3: Verify the complete release candidate and merge

**Files:**
- Verify: all repository files
- PR: `release/governed-0.18.0-publication` into `main`

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: one reviewed, exact-head release-control PR eligible for protected squash merge.

- [ ] **Step 1: Run the complete local-equivalent quality gate**

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: all tests pass, production statement and branch coverage remain 100%, and exactly one 0.18.0 wheel plus one 0.18.0 sdist are built.

- [ ] **Step 2: Open a draft PR with exact-head evidence**

The PR description records the public-package drift, security boundary, exact head, quality evidence, and the fact that GitHub Release creation and PyPI publication remain separately observable operations.

- [ ] **Step 3: Review every current-head comment and check**

Resolve actionable review threads, inspect every failed check log, update the branch only for evidence-backed corrections, and rerun all exact-head checks. Never reuse predecessor-head success.

- [ ] **Step 4: Mark ready and enable protected squash auto-merge**

Only after Python 3.10–3.13 CI, package smoke, Security Scan, SAST, review status, and unresolved-thread count satisfy repository rules.

- [ ] **Step 5: Confirm the merge commit and workflow bootstrap run**

Record the squash merge SHA and identify the `Create RankWeave Release` run started by the workflow-file push.

### Task 4: Verify GitHub Release and PyPI publication

**Files:**
- External evidence: GitHub Actions runs, GitHub Release, PyPI JSON API, downloaded distribution artifact
- Optional follow-up: naruon dependency update PR after success

**Interfaces:**
- Consumes: the merged release workflow and existing `publish.yml`.
- Produces: verifiable `v0.18.0` release and, when external configuration succeeds, public PyPI 0.18.0 distributions with attestations.

- [ ] **Step 1: Inspect the release-creation workflow**

Require success for verification, environment approval, duplicate recheck, and exact-SHA release creation. A queued or denied environment remains incomplete.

- [ ] **Step 2: Inspect the release-event publication workflow**

Require success for build, immutable handoff verification, GitHub provenance, protected publish, and PyPI upload. Diagnose failures from exact job logs without weakening the OIDC or attestation contract.

- [ ] **Step 3: Verify public PyPI metadata**

Fetch:

```text
https://pypi.org/pypi/rankweave/json
```

Require `info.version == "0.18.0"`, exactly one 0.18.0 wheel, exactly one 0.18.0 source distribution, and non-yanked files.

- [ ] **Step 4: Verify artifact identity and attestations**

Download the exact files and run the documented GitHub attestation verifier. Inspect PyPI's index-hosted PEP 740 attestation metadata. Do not claim vulnerability freedom or scientific validity from provenance alone.

- [ ] **Step 5: Start the naruon upgrade only after publication is verified**

Prepare a separate naruon PR replacing `rankweave==0.1.0` with `rankweave==0.18.0`, regenerate the hash lock, and add integration tests that exercise APIs introduced after 0.1.0. Do not combine the consumer upgrade with RankWeave release authorization.

## Plan self-review

- Spec coverage: authorization, least privilege, duplicate prevention, full quality gate, stable release, separate publication, failure handling, and post-publication verification are assigned to Tasks 1–4.
- Placeholder scan: no implementation placeholder or deferred validation remains.
- Interface consistency: the version is consistently `0.18.0`, tag `v0.18.0`, workflow `create-release.yml`, publisher `publish.yml`, and protected environment `pypi`.
