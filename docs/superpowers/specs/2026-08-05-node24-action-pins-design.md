# Node.js 24 Package CI Action Pin Hardening Design

## Status

Approved for autonomous implementation under the repository's standing commercialization loop. This is a bounded package-CI supply-chain hardening slice; it does not change RankWeave runtime APIs, report schemas, statistical behavior, package version, the privileged hourly product loop, or central reusable-workflow SHAs.

## Problem

RankWeave's repository-owned `ci.yml` still invokes older Node.js 20-based releases of `actions/checkout` and `actions/setup-python`. GitHub-hosted runners currently force those actions onto Node.js 24 and emit deprecation warnings. The warnings create avoidable operational noise, weaken the repository's evidence that checked-in automation matches its declared runtime, and can become future execution failures when the compatibility bridge is removed.

The existing regression test protects only the old checkout SHA. It does not assert setup-python or setup-uv and therefore cannot prove that every package-CI job uses the reviewed action set.

The privileged hourly commercialization workflow is deliberately excluded from this slice. It contains the autonomous-development credential and sandbox boundary and should receive its own narrowly reviewed control-plane PR rather than being coupled to ordinary package-CI maintenance.

## Considered approaches

### A. Keep old action commits and tolerate runner compatibility warnings

This preserves the exact existing workflow but depends on GitHub's temporary compatibility behavior. It gives no regression protection against future unsupported runtime removal. Rejected.

### B. Use moving action tags such as `@v6`

This removes manual SHA maintenance but allows upstream changes to enter privileged workflows without repository review. It conflicts with the repository's immutable action-pin policy. Rejected.

### C. Update package CI to current reviewed Node.js 24-compatible releases pinned by full commit SHA

Update `actions/checkout`, `actions/setup-python`, and `astral-sh/setup-uv` in both `ci.yml` jobs. Preserve every matrix entry, command, permission, checksum test, package smoke test, and release workflow. Expand tests to require exact counts and reject superseded commits. Recommended.

## Reviewed action identities

Official Git tag refs retrieved on August 5, 2026 resolve to:

- `actions/checkout` v6.0.2 — `de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `actions/setup-python` v6.2.0 — `a309ff8b426b58ec0e2a45f0f869d46889d02405`
- `astral-sh/setup-uv` v8.1.0 — `08807647e7069bb48b6ef5acd8ec9567f424441b`

The full commit SHA, not the mutable tag, is the workflow trust input.

## Scope

Replace both test/package job references for:

- `actions/checkout`
- `actions/setup-python`
- `astral-sh/setup-uv`

Do not alter Python 3.10–3.13 coverage, frozen uv installation, wheel/sdist inspection, checksum-handoff exercise, installed-wheel smoke, dependency checks, release publication, or autonomous-development controls.

## Regression contract

`tests/test_ci_supply_chain.py` must assert:

- exactly two current checkout, setup-python, and setup-uv references in `ci.yml`;
- no superseded checkout, setup-python, or setup-uv SHA remains in `ci.yml`;
- every asserted reference uses a 40-character lowercase hexadecimal commit SHA.

## Documentation

Record the trust decision in `docs/adr/0001-package-ci-action-runtime.md` and add the operational invariant to `CLAUDE.md`. The package changelog and version remain unchanged because no distributed Python behavior changes; the commit and ADR are the auditable CI-maintenance record.

## Failure handling

- A missing, duplicated, or stale action reference fails the normal pytest matrix.
- A moving action tag or shortened SHA fails the supply-chain regression test.
- The hourly commercialization workflow and central reusable-workflow SHAs are intentionally outside this replacement set.
- If any workflow behavior changes beyond package-CI action runtime and pin identity, the change is out of scope and must be split into a separate design.

## Verification

The exact head must pass Python 3.10, 3.11, 3.12, and 3.13 CI; Ruff; `compileall`; the complete pytest suite; 100% production statement and branch coverage; wheel and source-distribution inspection; checksum-handoff exercise; installed-wheel smoke; Security Scan; SAST Semgrep; and current-head review with no unresolved threads.
