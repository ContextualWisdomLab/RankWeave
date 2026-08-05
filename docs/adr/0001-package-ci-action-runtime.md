# ADR 0001: Pin package CI to reviewed Node.js 24-compatible actions

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** `.github/workflows/ci.yml`

## Context

GitHub-hosted runners currently execute older Node.js 20 action releases through a compatibility bridge and emit deprecation warnings. RankWeave treats workflow code as a supply-chain trust boundary, so a temporary runner fallback is not an acceptable long-term execution contract.

The package CI uses the same three actions in both its Python matrix and package job. Before this decision, only the checkout SHA had a regression test, and that test protected the superseded release.

## Decision

Package CI uses these reviewed action releases at their exact full commit SHAs:

- `actions/checkout` v6.0.2 — `de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `actions/setup-python` v6.2.0 — `a309ff8b426b58ec0e2a45f0f869d46889d02405`
- `astral-sh/setup-uv` v8.1.0 — `08807647e7069bb48b6ef5acd8ec9567f424441b`

The tag refs were resolved through the official GitHub repositories on August 5, 2026. Checked-in workflows use the commit SHA, not a mutable tag.

`tests/test_ci_supply_chain.py` enforces the exact two-job occurrence count for all three actions and rejects every superseded SHA.

## Consequences

- Package CI no longer depends on the Node.js 20 compatibility bridge.
- Upstream action changes still require a reviewed repository commit.
- Matrix, package, coverage, checksum, and installed-wheel behavior remain unchanged.
- Action updates require updating the workflow, the executable contract test, and this ADR together.
- The privileged hourly commercialization workflow is not modified by this decision and remains a separate control-plane review scope.

## Rejected alternatives

- **Keep the old releases:** rejected because temporary compatibility behavior can be withdrawn.
- **Use `@v6` or another moving tag:** rejected because it admits unreviewed upstream code into CI.
- **Update package CI and the autonomous control plane together:** rejected to keep the security review boundary narrow.
