# Node.js 24 Package CI Action Pin Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace deprecated Node.js 20 action releases in package CI with reviewed Node.js 24-compatible full-SHA pins without changing RankWeave runtime or autonomous-development behavior.

**Architecture:** Keep every existing CI job, permission, matrix value, command, and package assertion unchanged. Update only three package-CI action identities and make their exact counts, SHA form, and stale-pin absence executable repository contracts. The privileged hourly commercialization workflow remains a separate control-plane review slice.

**Tech Stack:** GitHub Actions, pytest, Python standard library, full-SHA action pinning.

## Global Constraints

- RankWeave runtime remains Python 3.10+ and standard-library-only.
- Package version remains `0.14.0`; this slice does not alter shipped APIs.
- Release publication, central reusable-workflow SHAs, hourly OpenCode/NVIDIA controls, schedules, permissions, and commands remain unchanged.
- Package-CI JavaScript actions use reviewed Node.js 24-compatible releases pinned to full 40-character commit SHAs.
- Production statement and branch coverage remain 100%; public production docstrings remain complete.

---

### Task 1: Specify the exact package-CI action-pin contract

**Files:**
- Modify: `tests/test_ci_supply_chain.py`

**Interfaces:**
- Consumes: `.github/workflows/ci.yml` as UTF-8 text.
- Produces: exact constants `CHECKOUT_SHA`, `SETUP_PYTHON_SHA`, and `SETUP_UV_SHA`; tests for expected counts, full-SHA syntax, and stale-pin absence.

- [ ] **Step 1: Replace the narrow checkout-only test with the complete failing contract**

```python
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
```

Assert two references for each current CI action, exact full-SHA extraction for those references, and absence of all superseded SHAs.

- [ ] **Step 2: Run the focused test and observe the red state**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_ci_supply_chain.py
```

Expected: FAIL because checked-in package CI still contains the superseded action commits.

- [ ] **Step 3: Commit the red contract**

```bash
git add tests/test_ci_supply_chain.py
git commit -m "test(red): require Node.js 24 package-CI pins"
```

### Task 2: Replace package-CI action pins

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_ci_supply_chain.py`

**Interfaces:**
- Consumes: exact SHA constants from Task 1.
- Produces: unchanged package-CI behavior executed through reviewed Node.js 24-compatible action releases.

- [ ] **Step 1: Update both CI job action sets**

Replace exactly:

```text
actions/checkout@11d5960a326750d5838078e36cf38b85af677262
→ actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd

actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
→ actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405

astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9
→ astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b
```

Keep every `with:`, command, matrix value, and job permission unchanged.

- [ ] **Step 2: Run the focused test**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_ci_supply_chain.py
```

Expected: PASS.

- [ ] **Step 3: Commit workflow hardening**

```bash
git add .github/workflows/ci.yml tests/test_ci_supply_chain.py
git commit -m "ci: pin Node.js 24-compatible package actions"
```

### Task 3: Synchronize governance documentation and verify the exact head

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-08-05-node24-action-pins-design.md`
- Modify: `docs/superpowers/plans/2026-08-05-node24-action-pins.md`

**Interfaces:**
- Consumes: the final checked-in package-CI action pins.
- Produces: maintainer guidance and release-history evidence without changing package version.

- [ ] **Step 1: Record the maintainer invariant**

Add a concise rule to both agent guidance files:

```text
Repository-owned package-CI JavaScript actions must use reviewed Node.js
24-compatible releases pinned to full commit SHAs. Moving tags and
compatibility-warning fallbacks are not accepted trust inputs.
```

- [ ] **Step 2: Update the Unreleased changelog**

Add `Changed` and `Security` entries describing the Node.js 24-compatible package-CI pins and expanded regression coverage. Do not create a new package release section.

- [ ] **Step 3: Run complete verification**

Run:

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: the complete suite passes; production statement/branch coverage remains 100%; wheel and source distribution build and pass existing inspection/smoke gates.

- [ ] **Step 4: Commit documentation**

```bash
git add AGENTS.md CLAUDE.md CHANGELOG.md \
  docs/superpowers/specs/2026-08-05-node24-action-pins-design.md \
  docs/superpowers/plans/2026-08-05-node24-action-pins.md
git commit -m "docs: govern package-CI action runtimes"
```

## Plan self-review

- **Spec coverage:** package-CI pins, stale-pin rejection, exact SHA syntax, separate hourly control-plane scope, documentation, and complete verification all map to tasks.
- **Placeholder scan:** no TBD, TODO, deferred implementation, or unspecified validation remains.
- **Name consistency:** the three action SHA constants match the reviewed official tag refs in every task.
- **Scope:** one package-CI supply-chain subsystem; no runtime Python, statistical, database, UI, release publication, hourly control-plane, or central workflow change.

## Execution mode

The standing commercialization loop selects inline execution with exact-head review and verification.
