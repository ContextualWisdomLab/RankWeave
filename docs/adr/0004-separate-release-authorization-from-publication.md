# ADR 0004: Separate release authorization from package publication

- **Status: Accepted**
- **Date:** 2026-08-06
- **Scope:** RankWeave stable GitHub Releases and PyPI publication

## Context

RankWeave's reviewed source tree declares version 0.18.0, while the public PyPI
project still exposes only 0.1.0. Naruon already imports RankWeave as its hybrid
retrieval compatibility seam but consequently pins the older public version.
The repository has a tokenless `publish.yml` pipeline for tests, immutable
artifact handoff, GitHub provenance, and PyPI Trusted Publishing, but it lacks a
permanent release-authorization entrypoint.

Creating a GitHub Release from a workflow with the repository `GITHUB_TOKEN`
does not trigger an ordinary `release`-event workflow. GitHub suppresses most
workflow-to-workflow events created by that token to prevent recursion, while
explicit `workflow_dispatch` and `repository_dispatch` events remain supported.
A release creator therefore cannot rely on its own `GITHUB_TOKEN`-authored
release event to start `publish.yml`.

## Decision

RankWeave separates the control plane into four least-privilege stages.

1. `.github/workflows/create-release.yml` verifies the exact default-branch
   commit, version identity, release uniqueness, public PyPI absence, complete
   quality gate, and deterministic release notes with `contents: read`.
2. A protected `pypi` environment job creates one stable GitHub Release with
   `contents: write` and no package credential.
3. A distinct job with only `actions: write` explicitly invokes the
   `workflow_dispatch` interface of `publish.yml`, passing the exact release tag
   and commit SHA. It cannot modify repository contents or publish a package.
4. `publish.yml` independently verifies that the stable GitHub Release and tag
   resolve to that exact commit, then retains its existing build, provenance,
   protected environment, OIDC, and PyPI Trusted Publishing jobs.

The release creator has a bounded bootstrap trigger only when its own workflow
file first reaches `main`, plus a manual `workflow_dispatch` interface requiring
an exact source-tree version. It is not a version-bump interface.

## Security properties

- Workflow-level permissions remain empty.
- No job possesses `contents: write`, `actions: write`, and `id-token: write`
  together.
- The repository stores no PyPI username, password, API token, GitHub personal
  access token, or GitHub App private key for release publication.
- All third-party actions use reviewed full commit SHAs.
- Existing tag, GitHub Release, or PyPI version state fails closed.
- The publisher accepts only a stable GitHub Release whose tag resolves to the
  exact released default-branch commit.
- `skip-existing`, force tag movement, alternate registries, and prerelease
  publication remain prohibited.

## Consequences

- Release authorization and package publication remain independently visible
  and independently retryable at their actual failure boundary.
- The explicit dispatch avoids storing a long-lived token merely to overcome
  GitHub's workflow-recursion protection.
- The `pypi` environment can require human approval before the public release is
  created and again before the package is uploaded.
- If release creation succeeds but publication fails, the public GitHub Release
  remains evidence of the authorized version; the failure must be repaired
  without deleting and recreating an immutable PyPI version.
- Naruon may upgrade its RankWeave pin only after the public distribution and
  attestations are independently verified.

## Rejected alternatives

- **Assume the release event will trigger:** false for an event created with the
  workflow `GITHUB_TOKEN` and therefore capable of silently leaving PyPI stale.
- **Use a personal access token or GitHub App private key:** adds a long-lived
  credential solely to trigger another workflow.
- **Publish inside the release-creation job:** combines repository mutation,
  package publication, and OIDC authority in one privileged failure domain.
- **Move or overwrite a tag:** destroys the immutable source-to-artifact binding.
- **Use `skip-existing`:** masks release identity errors instead of correcting
  versioning or external configuration.

## References — APA 7th edition

GitHub. (2026). *Triggering a workflow*. GitHub Docs.
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow

Python Packaging Authority. (2026). *Publishing package distribution releases
using GitHub Actions CI/CD workflows*. Python Packaging User Guide.
https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

Python Package Index. (2026). *Digital attestations*. PyPI Docs.
https://docs.pypi.org/attestations/

Python Package Index. (2026). *Publishing with a Trusted Publisher*. PyPI Docs.
https://docs.pypi.org/trusted-publishers/using-a-publisher/

Supply-chain Levels for Software Artifacts. (2026). *SLSA v1.2 provenance*.
https://slsa.dev/spec/v1.2/provenance
