# Trusted PyPI Release Design

## Status

Approved for autonomous implementation under the repository's standing commercialization loop. This is one bounded supply-chain and distribution slice; it does not change RankWeave runtime behavior or statistical contracts.

## Problem

RankWeave 0.14.0 is release-shaped but the README still requires installation from Git because PyPI Trusted Publishing is not configured. A buyer or naruon deployment therefore lacks a stable registry artifact, an environment-gated publication path, and independently verifiable build provenance.

A release workflow must not use long-lived PyPI API tokens. It must rebuild from the exact published GitHub Release tag, prove that the released commit, tag, and package version agree, run the complete quality gate, preserve and verify exact distribution bytes between jobs, generate GitHub build provenance, and publish through PyPI OIDC only after an environment gate.

## Considered approaches

### A. Twine with a stored PyPI API token

This is broadly compatible but creates a long-lived secret whose leakage can authorize package publication. Rotation and incident response become buyer-visible operational liabilities. Rejected.

### B. One job that builds and publishes with OIDC

This is simpler and follows the minimal PyPI example, but the build/test phase receives the same OIDC and environment context as publication. A single compromised step has a larger privilege surface, and there is no independently checked handoff between a non-publishing build and the publishing job. Rejected.

### C. Split build, provenance, and publish jobs with checksum-manifest verification

A read-only build job checks out the released tag, verifies release-event commit identity, default-branch reachability, tag/version identity, all tests and coverage, both archives, and required contents. It writes `release-handoff/SHA256SUMS`, exports the SHA-256 of that manifest as the unambiguous job output `manifest_sha256`, and uploads the distributions plus manifest as one immutable Actions artifact.

The provenance and protected `pypi` jobs download the same artifact, compare the downloaded manifest with the build-job output, verify the wheel and source-distribution hashes recorded by that manifest, and only then attest or publish the distributions. The manifest remains outside the package directory passed to PyPI. Recommended.

This explicit verification is required because the official download action has no `digest-mismatch` input. GitHub automatically validates the Actions artifact archive digest but reports a mismatch as a warning. RankWeave does not depend on an unsupported input or a warning-only decision for its distribution files.

## Workflow contract

Create `.github/workflows/publish.yml` with a single trigger:

```yaml
on:
  release:
    types: [published]
```

The workflow must not publish from `workflow_dispatch`, pull requests, branches, schedules, or reusable-workflow callers. GitHub Release creation remains an explicit human or governed release action.

### Build job

The build job:

1. checks out `github.event.release.tag_name` with full history and persisted credentials disabled;
2. requires a non-prerelease object and a tag of the exact form `vMAJOR.MINOR.PATCH`;
3. requires the checked-out commit to equal the release event commit;
4. requires the released commit to be reachable from the repository default branch;
5. reads `project.version` from `pyproject.toml` with Python 3.13 `tomllib`;
6. requires `tag == "v${project_version}"`;
7. requires `rankweave.__version__ == project_version`;
8. requires the version regression test to agree through the normal suite;
9. installs the frozen development environment with pinned uv;
10. runs `compileall`, Ruff, the complete pytest suite, and 100% statement/branch coverage;
11. builds wheel and sdist into `dist/`;
12. verifies that exactly one wheel and one sdist exist, names match the normalized version, and required wheel/sdist members exist;
13. writes `release-handoff/SHA256SUMS` for the exact wheel and sdist;
14. exports the manifest SHA-256 as `manifest_sha256`;
15. uploads `dist/` plus `release-handoff/SHA256SUMS` as one immutable artifact with hidden files excluded and missing files treated as an error.

The build job has only `contents: read`.

### Provenance job

The provenance job depends on the build job. It downloads `rankweave-distributions` into `handoff/`, verifies `handoff/release-handoff/SHA256SUMS` against `needs.build.outputs.manifest_sha256`, verifies both files in `handoff/dist/`, and invokes the current GitHub `actions/attest` release only for the wheel and source distribution.

Permissions match the pinned action's current provenance-mode contract:

```yaml
contents: read
id-token: write
attestations: write
artifact-metadata: write
```

This attestation establishes GitHub build provenance for the release distributions. It does not claim that PyPI configuration, package behavior, scientific inference, or downstream installation is trusted.

### PyPI publish job

The publish job depends on both build and provenance. It:

- uses the GitHub environment `pypi` with URL `https://pypi.org/p/rankweave`;
- has only `id-token: write` at job scope;
- downloads the same immutable artifact into `handoff/`;
- verifies the manifest digest and both distribution hashes before publication;
- passes only `handoff/dist/` to PyPI, excluding the checksum manifest;
- publishes through `pypa/gh-action-pypi-publish` v1.14.2 pinned by full commit SHA;
- supplies no username, password, API token, repository password, alternate repository, secret input, or skip-existing option;
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
- the workflow contains no manual, branch, PR, schedule, or reusable trigger;
- all `uses:` values are full 40-character SHAs from an allowlist;
- build, provenance, and publish jobs are separate and correctly ordered;
- the build job checks the stable release object, exact commit, default-branch reachability, package version, complete tests, coverage, wheel, and sdist;
- artifact upload/download use one expected immutable name and preserve the manifest outside the PyPI package directory;
- the build exports `manifest_sha256` as an independently trusted output;
- both downstream jobs verify the manifest digest and distribution checksums;
- the workflow contains no unsupported `digest-mismatch` input;
- provenance permissions include the pinned action's required artifact-metadata permission and `actions/attest` targets only the distributions;
- publishing uses environment `pypi`, OIDC, and no package-registry secret or fallback;
- no `COPILOT_GITHUB_TOKEN` appears.

The existing Python 3.10–3.13 matrix remains the runtime compatibility gate. The release build uses Python 3.13 as the deterministic packaging interpreter. The ordinary pull-request package job also builds and inspects the source distribution, so archive completeness is exercised before a GitHub Release can exist.

## Documentation and operational setup

Create `docs/releasing.md` with the one-time external setup and governed release procedure:

1. create or claim the PyPI `rankweave` project;
2. configure a pending or normal GitHub Trusted Publisher for owner `ContextualWisdomLab`, repository `RankWeave`, workflow `publish.yml`, environment `pypi`;
3. create a protected GitHub `pypi` environment with required reviewers;
4. merge a versioned release commit whose `pyproject.toml`, `rankweave.__version__`, test expectation, CHANGELOG, and installed-wheel assertions agree;
5. publish a stable GitHub Release whose tag is exactly `v${version}` and whose commit is on default-branch history;
6. verify GitHub attestations with `gh attestation verify` and PyPI attestations through PyPI's supported verifier.

README, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`, and `CHANGELOG.md` are updated. The package stays at 0.14.0 because this slice enables distribution of the already-versioned release and changes no shipped runtime API.

## Standards and source boundary

The research documentation records APA 7 references to PyPI Trusted Publishing, PEP 740 index-hosted attestations, GitHub Artifact Attestations, GitHub workflow-artifact validation, and the SLSA provenance model. Documentation must distinguish:

- the workflow artifact's automatically checked archive digest, which is warning-only on mismatch;
- RankWeave's fail-closed manifest and distribution checksum verification;
- GitHub provenance attestation for the workflow-built files;
- PyPI index-hosted attestations created during Trusted Publishing;
- exact artifact bytes downloaded by consumers;
- package correctness and scientific validity, which none of these controls proves.

## Failure handling

- Prerelease, non-canonical tag, event/checkout commit mismatch, default-branch reachability failure, or tag/version mismatch fails before build or OIDC publication.
- Any test, coverage, archive inspection, upload, manifest mismatch, distribution checksum mismatch, provenance, environment approval, OIDC, or PyPI error fails the workflow.
- Re-running a published release against a version already present on PyPI is not silently skipped.
- The workflow never falls back to a stored token or alternate repository.
- No release is claimed complete until the published package and both attestation surfaces are independently verified.
