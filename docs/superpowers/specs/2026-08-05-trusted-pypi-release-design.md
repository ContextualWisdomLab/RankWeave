# Trusted PyPI Release Design

## Status

Approved for autonomous implementation under the repository's standing commercialization loop. This is one bounded supply-chain and distribution slice; it does not change RankWeave runtime behavior or statistical contracts.

## Problem

RankWeave 0.14.0 is release-shaped but the README still requires installation from Git because PyPI Trusted Publishing is not configured. A buyer or naruon deployment therefore lacks a stable registry artifact, an environment-gated publication path, and independently verifiable build provenance.

A release workflow must not use long-lived PyPI API tokens. It must rebuild from the exact published GitHub Release tag, prove that the tag and package version agree, run the complete quality gate, preserve immutable build artifacts between jobs, generate GitHub build provenance, and publish through PyPI OIDC only after an environment gate.

## Considered approaches

### A. Twine with a stored PyPI API token

This is broadly compatible but creates a long-lived secret whose leakage can authorize package publication. Rotation and incident response become buyer-visible operational liabilities. Rejected.

### B. One job that builds and publishes with OIDC

This is simpler and follows the minimal PyPI example, but the build/test phase receives the same OIDC and environment context as publication. A single compromised step has a larger privilege surface, and there is no immutable handoff between a non-publishing build and the publishing job. Rejected.

### C. Split build, provenance, and publish jobs

A read-only build job checks out the released tag, verifies tag/version identity, runs all tests and coverage, builds both wheel and sdist, inspects their contents, and uploads one immutable Actions artifact. A provenance job downloads the exact artifact and generates GitHub attestations. A separate `pypi` environment job downloads the same artifact and uses PyPI Trusted Publishing with only `id-token: write`. Recommended.

## Workflow contract

Create `.github/workflows/publish.yml` with a single trigger:

```yaml
on:
  release:
    types: [published]
```

The workflow must not publish from `workflow_dispatch`, pull requests, branches, or reusable-workflow callers. GitHub Release creation remains an explicit human or governed release action.

### Build job

The build job:

1. checks out `github.event.release.tag_name` with persisted credentials disabled;
2. requires a tag of the exact form `vMAJOR.MINOR.PATCH`;
3. reads `project.version` from `pyproject.toml` with Python 3.13 `tomllib`;
4. requires `tag == "v${project_version}"`;
5. requires `rankweave.__version__ == project_version`;
6. requires the version regression test to agree through the normal suite;
7. installs the frozen development environment with pinned uv;
8. runs `compileall`, Ruff, the complete pytest suite, and 100% statement/branch coverage;
9. builds wheel and sdist into `dist/`;
10. verifies that exactly one wheel and one sdist exist and that both names contain the expected normalized version;
11. verifies wheel resources and the sdist's release files;
12. uploads `dist/` as one immutable artifact with hidden files excluded and missing files treated as an error.

The build job has only `contents: read`.

### Provenance job

The provenance job depends on the build job, downloads the immutable artifact with digest mismatch configured to fail, and invokes the current GitHub `actions/attest` release on `dist/*`.

Permissions are exactly:

```yaml
contents: read
id-token: write
attestations: write
```

This attestation establishes GitHub build provenance for the release artifacts. It does not claim that PyPI configuration, package behavior, or downstream installation is trusted.

### PyPI publish job

The publish job depends on both build and provenance. It:

- uses the GitHub environment `pypi` with URL `https://pypi.org/p/rankweave`;
- has only `id-token: write` at job scope;
- downloads the same immutable artifact;
- publishes through `pypa/gh-action-pypi-publish` v1.14.2 pinned by full commit SHA;
- supplies no username, password, API token, repository password, or secret input;
- leaves PyPI's PEP 740 attestation generation enabled.

Publication must fail closed until the PyPI project has a matching pending or normal Trusted Publisher and the GitHub `pypi` environment permits the job.

## Immutable action versions

The workflow uses current stable, Node.js 24-compatible releases pinned to full commit SHA:

- `actions/checkout` v6.0.2 — `de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `actions/setup-python` v6.2.0 — `a309ff8b426b58ec0e2a45f0f869d46889d02405`
- `astral-sh/setup-uv` v8.1.0 — `08807647e7069bb48b6ef5acd8ec9567f424441b`
- `actions/upload-artifact` v7.0.1 — `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`
- `actions/download-artifact` v8.0.1 — `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`
- `actions/attest` v4.2.2 — `1e69f48acb82d1966a394da916b4c1698aa569d6`
- `pypa/gh-action-pypi-publish` v1.14.2 — `dc37677b2e1c63e2034f94d8a5b11f265b73ba33`

## Tests

`tests/test_publish_workflow.py` treats the workflow as a security-sensitive contract and verifies:

- only `release: published` can trigger publication;
- the workflow contains no `workflow_dispatch`, `pull_request`, `push`, or `workflow_call` trigger;
- all `uses:` values are full 40-character SHAs from an allowlist;
- build, provenance, and publish jobs are separate and correctly ordered;
- the build job checks released tag, package version, complete tests, coverage, wheel, and sdist;
- artifact upload/download use the expected immutable names and fail-closed options;
- provenance permissions are minimal and `actions/attest` is present;
- publishing uses environment `pypi`, OIDC, and no package-registry secret;
- no `COPILOT_GITHUB_TOKEN` appears.

The existing Python 3.10–3.13 matrix remains the runtime compatibility gate. The release build uses Python 3.13 as the deterministic packaging interpreter.
The ordinary pull-request package job also builds and inspects the source distribution, so archive completeness is exercised before a GitHub Release can exist.

## Documentation and operational setup

Create `docs/releasing.md` with the one-time external setup and governed release procedure:

1. create or claim the PyPI `rankweave` project;
2. configure a pending or normal GitHub Trusted Publisher for owner `ContextualWisdomLab`, repository `RankWeave`, workflow `publish.yml`, environment `pypi`;
3. create a protected GitHub `pypi` environment with required reviewers;
4. merge a versioned release commit whose `pyproject.toml`, `rankweave.__version__`, test expectation, CHANGELOG, and installed-wheel assertions agree;
5. publish a GitHub Release whose tag is exactly `v${version}`;
6. verify GitHub attestations with `gh attestation verify` and PyPI attestations through PyPI's supported verifier.

README, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`, and `CHANGELOG.md` are updated. The package stays at 0.14.0 because this slice enables distribution of the already-versioned release and changes no shipped runtime API.

## Standards and source boundary

The research documentation records APA 7 references to PyPI Trusted Publishing, PEP 740 index-hosted attestations, GitHub Artifact Attestations, and the SLSA provenance model. Documentation must distinguish:

- GitHub provenance attestation for the workflow-built files;
- PyPI index-hosted attestations created during Trusted Publishing;
- exact artifact bytes downloaded by consumers;
- package correctness and scientific validity, which neither attestation proves.

## Failure handling

- Tag/version mismatch fails before build or OIDC publication.
- Any test, coverage, archive inspection, upload, digest download, provenance, environment approval, OIDC, or PyPI error fails the workflow.
- Re-running a published release against a version already present on PyPI is not silently skipped.
- The workflow never falls back to a stored token or alternate repository.
- No release is claimed complete until the published package and both attestation surfaces are independently verified.
