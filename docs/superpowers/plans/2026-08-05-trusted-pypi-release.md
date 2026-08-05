# Trusted PyPI Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tokenless, environment-gated, attested PyPI publication workflow for the already-versioned RankWeave 0.14.0 release.

**Architecture:** A read-only build job validates the exact stable GitHub Release object, released commit, default-branch reachability, package version, full quality gate, wheel, and source distribution. It writes `release-handoff/SHA256SUMS`, exports the manifest digest as `manifest_sha256`, and uploads `dist/` plus the manifest as one immutable Actions artifact. Separate provenance and protected `pypi` jobs download into `handoff/`, verify the manifest and both distributions, and then attest or publish only `handoff/dist/`.

**Tech Stack:** GitHub Actions, uv 0.11.29, Python 3.13 `tomllib`, GNU `sha256sum`, PyPI Trusted Publishing, PEP 740 attestations, GitHub Artifact Attestations, pytest, Ruff, coverage.py.

## Global Constraints

- RankWeave runtime remains Python 3.10+ and standard-library-only.
- The package version remains exactly `0.14.0`; this slice changes release infrastructure, not runtime APIs.
- Every third-party action is pinned to a full 40-character commit SHA.
- Publication is triggered only by a published, non-prerelease GitHub Release.
- The checked-out tag commit must equal the release event commit and be reachable from the default branch.
- PyPI authentication uses OIDC Trusted Publishing; no username, password, API token, or package-registry secret is permitted.
- The publishing job uses the protected GitHub environment `pypi`.
- Build, provenance, and publication are separate jobs with least privilege.
- The provenance job includes `artifact-metadata: write`, as required by the pinned `actions/attest` release.
- Downstream jobs verify `needs.build.outputs.manifest_sha256` and then verify the wheel and sdist checksums.
- The manifest remains outside the directory passed to the PyPI action.
- The workflow does not use the nonexistent `download-artifact` input `digest-mismatch`; GitHub's automatic archive validation is warning-only on mismatch.
- Existing 100% production statement/branch coverage and production docstring gates remain intact.
- Existing CI, hourly automation, NVIDIA/OpenCode secrets, and central reusable-workflow SHAs are unchanged.

---

### Task 1: Add failing release-workflow security contracts

**Files:**
- Create: `tests/test_publish_workflow.py`
- Test: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes repository text files under `.github/workflows/` and `docs/releasing.md`.
- Produces text-level regression tests defining trigger, commit identity, version, job, permission, checksum, provenance, publication, and documentation contracts.

- [ ] **Step 1: Write the red tests**

Require:

```python
assert "on:\n  release:\n    types: [published]\n" in trigger_block
assert "workflow_dispatch:" not in trigger_block
assert "RELEASE_PRERELEASE" in build_block
assert '"merge-base",' in build_block
assert '"--is-ancestor",' in build_block
assert "manifest_sha256" in build_block
assert "release-handoff/SHA256SUMS" in build_block
assert "digest-mismatch:" not in workflow_text
assert "EXPECTED_MANIFEST_SHA256" in provenance_block
assert "EXPECTED_MANIFEST_SHA256" in publish_block
assert "packages-dir: handoff/dist/" in publish_block
assert "artifact-metadata: write" in provenance_block
assert "environment:\n      name: pypi\n" in publish_block
assert "PYPI_API_TOKEN" not in publish_block
```

Require the exact allowlisted action SHAs:

```python
EXPECTED_ACTIONS = {
    "actions/checkout": "de0fac2e4500dabe0009e67214ff5f5447ce83dd",
    "actions/setup-python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "astral-sh/setup-uv": "08807647e7069bb48b6ef5acd8ec9567f424441b",
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "actions/download-artifact": "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
    "actions/attest": "1e69f48acb82d1966a394da916b4c1698aa569d6",
    "pypa/gh-action-pypi-publish": "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
}
```

- [ ] **Step 2: Run focused tests and observe the red state**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_publish_workflow.py
```

Expected: FAIL because `.github/workflows/publish.yml` and `docs/releasing.md` do not yet exist.

- [ ] **Step 3: Commit the red contracts**

```bash
git add tests/test_publish_workflow.py
git commit -m "test(red): specify tokenless attested PyPI releases"
```

### Task 2: Implement the release-only build and immutable handoff

**Files:**
- Create: `.github/workflows/publish.yml`
- Modify: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes GitHub Release event fields, default-branch Git history, `pyproject.toml`, `rankweave.__version__`, `uv.lock`, and repository tests.
- Produces Actions artifact `rankweave-distributions` containing `dist/`, `release-handoff/SHA256SUMS`, and build output `manifest_sha256`.

- [ ] **Step 1: Create the release-only workflow skeleton**

```yaml
name: Publish RankWeave

on:
  release:
    types: [published]

permissions: {}

concurrency:
  group: publish-${{ github.event.release.tag_name }}
  cancel-in-progress: false
```

- [ ] **Step 2: Implement the read-only build job**

Use checkout v6.0.2 with `fetch-depth: 0`, setup-python v6.2.0, and setup-uv v8.1.0 at the exact SHAs above. Set `persist-credentials: false` and grant only `contents: read`.

Validate:

```text
release.prerelease == false
release tag matches vMAJOR.MINOR.PATCH
checked-out HEAD == github.sha
HEAD is an ancestor of origin/${default_branch}
tag == v${project.version}
rankweave.__version__ == project.version
```

Run frozen sync, compileall, Ruff, complete pytest coverage, `uv build --wheel --sdist --out-dir dist`, and archive inspection.

- [ ] **Step 3: Record the distribution manifest and immutable output**

```bash
mkdir -p release-handoff
(
  cd dist
  sha256sum *.whl *.tar.gz
) > release-handoff/SHA256SUMS
manifest_sha256="$(
  sha256sum release-handoff/SHA256SUMS | cut -d ' ' -f1
)"
printf 'manifest_sha256=%s\n' "$manifest_sha256" >> "$GITHUB_OUTPUT"
```

Expose `steps.distributions.outputs.manifest_sha256` as the build job output. Upload:

```yaml
path: |
  dist/
  release-handoff/SHA256SUMS
```

Use `if-no-files-found: error`, `include-hidden-files: false`, and seven-day retention.

- [ ] **Step 4: Run focused tests**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_publish_workflow.py
```

Expected: publication trigger, exact action pins, release identity, build gate, manifest, and upload contracts pass.

### Task 3: Implement verified provenance and protected publication

**Files:**
- Modify: `.github/workflows/publish.yml`
- Modify: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes the immutable artifact and `needs.build.outputs.manifest_sha256`.
- Produces GitHub provenance attestations for wheel/sdist and PyPI publication through environment `pypi`.

- [ ] **Step 1: Implement the provenance job**

```yaml
provenance:
  needs: build
  permissions:
    contents: read
    id-token: write
    attestations: write
    artifact-metadata: write
```

Download into `handoff/`, then fail closed:

```bash
printf '%s  %s\n' \
  "$EXPECTED_MANIFEST_SHA256" \
  handoff/release-handoff/SHA256SUMS | \
  sha256sum --check --strict -
(
  cd handoff/dist
  sha256sum --check --strict ../release-handoff/SHA256SUMS
)
```

Attest only `handoff/dist/*.whl` and `handoff/dist/*.tar.gz` through actions/attest v4.2.2.

- [ ] **Step 2: Implement the protected PyPI job**

```yaml
publish:
  needs: [build, provenance]
  environment:
    name: pypi
    url: https://pypi.org/p/rankweave
  permissions:
    id-token: write
```

Repeat the same fail-closed manifest and file verification, then invoke `pypa/gh-action-pypi-publish` v1.14.2 with only:

```yaml
packages-dir: handoff/dist/
```

Do not add credentials, alternate repository, skip-existing inputs, or the checksum manifest to the package directory.

- [ ] **Step 3: Run focused and complete tests**

```bash
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
```

Expected: complete suite passes with production statement and branch coverage at 100%.

### Task 4: Exercise both release archives in ordinary pull-request CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_publish_workflow.py`

- [ ] **Step 1: Build wheel and sdist in the package job**

```bash
uv build --wheel --sdist --out-dir dist
```

- [ ] **Step 2: Inspect source-distribution contents**

Require exactly one `rankweave-*.tar.gz` and verify:

```text
pyproject.toml
README.md
CHANGELOG.md
LICENSE
src/rankweave/__init__.py
tests/test_version.py
```

- [ ] **Step 3: Add workflow regression assertions**

Require the sdist build command, inspection step, exact-count failure, CHANGELOG, and version test in `tests/test_publish_workflow.py`.

- [ ] **Step 4: Run complete verification**

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

### Task 5: Document setup, provenance boundaries, and release operations

**Files:**
- Create: `docs/releasing.md`
- Create: `docs/research/trusted-release-provenance.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_publish_workflow.py`

- [ ] **Step 1: Document exact external configuration**

```text
PyPI project: rankweave
Owner: ContextualWisdomLab
Repository: RankWeave
Workflow: publish.yml
Environment: pypi
```

Document required environment reviewers, release tag `v${version}`, stable/default-branch commit gate, publication failure modes, seven-day workflow-artifact retention, PyPI as the durable distribution surface, `gh attestation verify`, and PyPI PEP 740 verification. State that external PyPI and GitHub environment setup cannot be completed by repository code.

- [ ] **Step 2: Synchronize architecture and contributor contracts**

Document:

```text
exact stable release object
-> full quality gate
-> wheel and sdist inspection
-> release-handoff/SHA256SUMS plus manifest_sha256 output
-> immutable workflow artifact
-> verified handoff/dist distributions
-> GitHub provenance
-> protected PyPI OIDC publication
```

Prohibit registry-token fallback, unsupported action inputs, `skip-existing`, and claims that attestations prove scientific validity.

- [ ] **Step 3: Add APA 7 references**

```text
Python Packaging Authority. (n.d.). Publishing with a Trusted Publisher. PyPI documentation. Retrieved August 5, 2026, from https://docs.pypi.org/trusted-publishers/using-a-publisher/

Trail of Bits. (2023). PEP 740—Index support for digital attestations. Python Enhancement Proposals. https://peps.python.org/pep-0740/

GitHub. (n.d.). Using artifact attestations to establish provenance for builds. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

GitHub. (n.d.). Storing and sharing data from a workflow. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow

Supply-chain Levels for Software Artifacts. (n.d.). Build: Verifying artifacts (SLSA specification v1.2). OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts
```

- [ ] **Step 4: Verify documentation contracts and complete suite**

```bash
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
```

## Plan self-review

- **Spec coverage:** stable release identity, default-branch reachability, tag/version gate, complete build gate, wheel/sdist inspection, explicit manifest verification, current attest permissions, PyPI OIDC, environment protection, PR archive testing, documentation, and trust boundaries map to tasks.
- **Placeholder scan:** no TBD, TODO, deferred implementation, or unspecified validation remains.
- **Type and name consistency:** artifact name is always `rankweave-distributions`; manifest is always `release-handoff/SHA256SUMS`; job output is always `manifest_sha256`; package directory is always `handoff/dist/`; environment is always `pypi`; workflow is always `publish.yml`; action SHAs match the design.
- **Scope:** one supply-chain/distribution subsystem; no runtime API, statistical model, database, or UI changes.

## Execution mode

The repository's standing autonomous loop selects inline execution with exact-head review and verification. Every task remains independently reviewable through its tests and commits before the PR is marked ready.
