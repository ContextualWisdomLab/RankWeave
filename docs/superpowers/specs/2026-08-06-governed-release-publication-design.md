# Governed RankWeave Publication Design

- **Status:** Approved for autonomous implementation
- **Date:** 2026-08-06
- **Scope:** Stable GitHub Release creation for the already prepared RankWeave 0.18.0 package

## Problem

RankWeave's source tree and package metadata are at 0.18.0, while the public PyPI project still exposes only 0.1.0. The naruon backend consequently pins `rankweave==0.1.0` and cannot consume the audited tuning, cross-validation, temporal-backtesting, report-schema, artifact-verification, and package-provenance work already present on RankWeave `main`.

The repository already contains a publishing workflow that builds, tests, attests, and uploads distributions through PyPI Trusted Publishing. The missing product boundary is a governed way to create the exact stable GitHub Release and explicitly dispatch publication: GitHub does not start an ordinary release-event workflow for a Release created with the repository `GITHUB_TOKEN`.

## Goals

1. Add a permanent, manually reusable GitHub Release workflow.
2. Bootstrap the first stable release, `v0.18.0`, when this workflow reaches `main`.
3. Refuse ambiguous, stale, prerelease, duplicate, or version-mismatched releases.
4. Run the complete package quality gate before creating a public release.
5. Use only the repository-scoped `GITHUB_TOKEN`; do not introduce a long-lived package or GitHub credential.
6. Preserve the existing protected `pypi` environment and Trusted Publisher identity.
7. Keep publication and release creation separate: the new workflow creates a GitHub Release, while `publish.yml` remains the sole PyPI publisher.

## Non-goals

- Bypassing PyPI Trusted Publisher configuration or GitHub environment approval.
- Publishing with a username, password, API token, or `COPILOT_GITHUB_TOKEN`.
- Re-publishing an existing PyPI version or using `skip-existing`.
- Automatically updating naruon before PyPI publication and artifact verification succeed.
- Creating release assets outside the existing immutable workflow artifact and PyPI distribution surfaces.

## Selected approach

Add `.github/workflows/create-release.yml` with two triggers:

- `workflow_dispatch`, taking an exact semantic version such as `0.18.0`;
- a bounded bootstrap `push` trigger that fires only when this workflow file itself is first merged to `main`.

The workflow has a read-only `verify` job followed by a protected `release` job with only `contents: write`. A third job with only `actions: write` invokes the exact-tag/exact-SHA `workflow_dispatch` interface of `publish.yml`. The publisher independently verifies the existing stable GitHub Release before build, provenance, and OIDC upload.

This approach leaves a reusable, reviewable release control plane without a personal access token or GitHub App private key. It separates release mutation, workflow dispatch, build provenance, and package publication so no job receives all authorities.

## Validation contract

The workflow must fail unless all of the following hold:

- the requested version matches `[0-9]+.[0-9]+.[0-9]+`;
- `pyproject.toml`, `rankweave.__version__`, `tests/test_version.py`, and the latest `CHANGELOG.md` release heading agree;
- the checked-out SHA is exactly the workflow event SHA;
- the commit is reachable from `origin/main`;
- the package version is not already present on PyPI;
- neither `refs/tags/v${version}` nor a GitHub Release for that tag exists;
- compile, Ruff, the complete test suite, 100% statement/branch coverage, wheel and source build, and archive-content checks pass;
- the release is not a prerelease or draft.

The bootstrap push path may only publish the version already declared by the merged source tree. Manual dispatch must also match the source-tree version; it is not a version-bump interface.

## Data flow

```mermaid
flowchart LR
    M[Governed main commit] --> V[Read-only release verification]
    V --> Q[Full package quality gate]
    Q --> E[pypi environment approval]
    E --> R[Stable GitHub Release v0.18.0]
    R --> D[Explicit workflow_dispatch]
    D --> P[Existing publish.yml]
    P --> A[GitHub build provenance]
    A --> Y[PyPI Trusted Publishing]
    Y --> C[naruon dependency upgrade]
```

## Security boundaries

- Workflow-level permissions are empty.
- Verification uses `contents: read` only.
- Release creation uses `contents: write` only and is isolated in the protected environment.
- Checkout actions remain pinned by full commit SHA and disable persisted credentials.
- The release command receives the event token through `GH_TOKEN` only in the release step.
- Release notes are extracted deterministically from `CHANGELOG.md`; no untrusted PR text or LLM output enters a shell command.
- Existing PyPI publication remains OIDC-based with `id-token: write` and no registry secret.

## Testing

Repository contract tests will assert:

- exact supported triggers and bootstrap path;
- full-SHA action pins;
- least privilege by job;
- protected environment use;
- exact version, ancestry, duplicate-tag, duplicate-release, and PyPI-release checks;
- complete quality-gate commands before release creation;
- stable, non-draft, non-prerelease release options;
- absence of package credentials, `COPILOT_GITHUB_TOKEN`, `skip-existing`, force tag movement, and alternate registry fallback;
- release documentation and CHANGELOG describe the boundary accurately.

## Failure handling

A queued environment approval is not treated as success. A missing Trusted Publisher, environment denial, explicit dispatch failure, OIDC failure, PyPI conflict, or attestation failure remains visible and must be corrected without weakening the contract. If the GitHub Release succeeds but publication fails, the same version is not recreated; publication may be re-dispatched only after the exact stable release and source remain valid, otherwise a new patch version is prepared.

## Standards and authority

The design follows PyPI Trusted Publishing guidance, the Python Packaging User Guide's GitHub Actions publication pattern, PyPI's PEP 740 attestation model, GitHub OIDC least-secret guidance, and SLSA v1.2 provenance terminology. The repository claims only the narrower artifact identity and provenance properties actually produced by its workflows.
