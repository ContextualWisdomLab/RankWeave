# Trusted PyPI Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tokenless, environment-gated, attested PyPI publication workflow for the already-versioned RankWeave 0.14.0 release and move repository-owned JavaScript actions to pinned Node.js 24-compatible releases.

**Architecture:** A read-only build job rebuilds and validates the exact GitHub Release tag, then uploads one immutable distribution artifact. Separate provenance and `pypi` environment jobs download that artifact; the former creates GitHub build provenance and the latter publishes with PyPI OIDC and no registry secret. Stdlib tests enforce the workflow as a security contract.

**Tech Stack:** GitHub Actions, uv 0.11.29, Python 3.13 `tomllib`, PyPI Trusted Publishing, PEP 740 attestations, GitHub Artifact Attestations, pytest, Ruff, coverage.py.

## Global Constraints

- RankWeave runtime remains Python 3.10+ and standard-library-only.
- The package version remains exactly `0.14.0`; this slice changes release infrastructure, not runtime APIs.
- Every third-party action is pinned to a full 40-character commit SHA.
- Publication is triggered only by a published GitHub Release.
- PyPI authentication uses OIDC Trusted Publishing; no username, password, API token, or package-registry secret is permitted.
- The publishing job uses the protected GitHub environment `pypi`.
- Build, provenance, and publication are separate jobs with least privilege.
- Existing 100% production statement/branch coverage and production docstring gates remain intact.
- Existing NVIDIA/OpenCode autonomous workflow secrets and central reusable-workflow SHAs are unchanged.

---

### Task 1: Add failing release-workflow security contracts

**Files:**
- Create: `tests/test_publish_workflow.py`
- Test: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes: repository text files under `.github/workflows/`.
- Produces: `_workflow_text(path: str) -> str`, `_action_references(text: str) -> tuple[str, ...]`, and regression tests that define the complete publication contract.

- [ ] **Step 1: Write the failing workflow tests**

```python
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SHA_ACTION = re.compile(r"uses:\s+([^\s@]+)@([0-9a-f]{40})(?:\s|$)")

EXPECTED_ACTIONS = {
    "actions/checkout": "de0fac2e4500dabe0009e67214ff5f5447ce83dd",
    "actions/setup-python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "astral-sh/setup-uv": "08807647e7069bb48b6ef5acd8ec9567f424441b",
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "actions/download-artifact": "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
    "actions/attest": "1e69f48acb82d1966a394da916b4c1698aa569d6",
    "pypa/gh-action-pypi-publish": "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
}


def _workflow_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_publish_workflow_is_release_only_and_tokenless():
    text = _workflow_text(".github/workflows/publish.yml")
    assert "release:" in text
    assert "types: [published]" in text
    assert "workflow_dispatch:" not in text
    assert "PYPI_API_TOKEN" not in text
    assert "password:" not in text
    assert "environment:" in text and "name: pypi" in text


def test_publish_workflow_separates_build_provenance_and_publish():
    text = _workflow_text(".github/workflows/publish.yml")
    assert "  build:" in text
    assert "  provenance:" in text
    assert "  publish:" in text
    assert "needs: build" in text
    assert "needs: [build, provenance]" in text
    assert "uv run --frozen --extra dev --python 3.13 python -m coverage report" in text
    assert "github.event.release.tag_name" in text


def test_publish_workflow_pins_every_external_action():
    text = _workflow_text(".github/workflows/publish.yml")
    found = dict(SHA_ACTION.findall(text))
    assert found == EXPECTED_ACTIONS
```

Add focused tests for exact job permissions, immutable artifact name `rankweave-distributions`, `if-no-files-found: error`, `include-hidden-files: false`, download `digest-mismatch: error`, `subject-path: dist/*`, `environment.url`, and the absence of `COPILOT_GITHUB_TOKEN`.

- [ ] **Step 2: Run the focused tests and observe the red state**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_publish_workflow.py
```

Expected: FAIL because `.github/workflows/publish.yml` does not exist and current CI/hourly action SHAs do not match the Node.js 24 allowlist.

- [ ] **Step 3: Commit the red contracts**

```bash
git add tests/test_publish_workflow.py
git commit -m "test(red): specify tokenless attested PyPI releases"
```

### Task 2: Implement the split release workflow

**Files:**
- Create: `.github/workflows/publish.yml`
- Test: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes: GitHub Release event fields, `pyproject.toml`, `src/rankweave/__init__.py`, `uv.lock`, and repository tests.
- Produces: immutable Actions artifact `rankweave-distributions`, GitHub attestations for `dist/*`, and PyPI publication through environment `pypi`.

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

Use checkout v6.0.2, setup-python v6.2.0, and setup-uv v8.1.0 at the exact SHAs in the design. Set `persist-credentials: false`, checkout `github.event.release.tag_name`, and grant only `contents: read`.

Add a Python `tomllib` step that:

```python
from pathlib import Path
import os
import re
import tomllib

release_tag = os.environ["RELEASE_TAG"]
if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", release_tag) is None:
    raise SystemExit(f"release tag is not canonical: {release_tag!r}")
project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
version = project["project"]["version"]
if release_tag != f"v{version}":
    raise SystemExit(
        f"release tag {release_tag!r} does not match project version {version!r}"
    )
Path(os.environ["GITHUB_OUTPUT"]).write_text(
    f"version={version}\n",
    encoding="utf-8",
)
```

Then run frozen sync, compileall, Ruff, full coverage, `uv build --wheel --sdist --out-dir dist`, archive inspection, and upload through `actions/upload-artifact` v7.0.1 with `if-no-files-found: error`, `include-hidden-files: false`, and `retention-days: 7`.

- [ ] **Step 3: Implement the provenance job**

```yaml
  provenance:
    needs: build
    permissions:
      contents: read
      id-token: write
      attestations: write
```

Download `rankweave-distributions` using download-artifact v8.0.1 with `digest-mismatch: error`, then call actions/attest v4.2.2 with `subject-path: dist/*`.

- [ ] **Step 4: Implement the protected PyPI publishing job**

```yaml
  publish:
    needs: [build, provenance]
    environment:
      name: pypi
      url: https://pypi.org/p/rankweave
    permissions:
      id-token: write
```

Download the same artifact with digest mismatch failure and invoke `pypa/gh-action-pypi-publish` v1.14.2 at its exact SHA. Do not add any action inputs for credentials or alternate repositories.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_publish_workflow.py
```

Expected: PASS for release-only trigger, job separation, least privilege, pinned actions, artifact handoff, provenance, and tokenless publication.

- [ ] **Step 6: Commit the workflow**

```bash
git add .github/workflows/publish.yml tests/test_publish_workflow.py
git commit -m "ci: add tokenless attested PyPI publication"
```

### Task 3: Migrate repository-owned actions to Node.js 24 releases

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/hourly-commercialization-loop.yml`
- Test: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes: the current CI and hourly workflow behavior.
- Produces: identical behavior with pinned checkout v6.0.2, setup-python v6.2.0, and setup-uv v8.1.0 action runtimes.

- [ ] **Step 1: Extend tests to enforce Node.js 24 action SHAs**

```python
@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        ".github/workflows/hourly-commercialization-loop.yml",
    ],
)
def test_repository_owned_workflows_use_current_node24_actions(path):
    text = _workflow_text(path)
    assert "actions/checkout@11d5960" not in text
    assert "actions/setup-python@a26af69" not in text
    assert "astral-sh/setup-uv@c771a70" not in text
```

Also assert that every occurrence uses the allowlisted full SHA. The hourly workflow's central reusable workflow SHAs and OpenCode/NVIDIA configuration must remain byte-identical.

- [ ] **Step 2: Run the focused test and observe failure**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_publish_workflow.py
```

Expected: FAIL on the older checkout/setup action SHAs.

- [ ] **Step 3: Replace only repository-owned action references**

Replace:

```text
actions/checkout@11d5960a326750d5838078e36cf38b85af677262
→ actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd

actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
→ actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405

astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9
→ astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b
```

Update comments to v6.0.2, v6.2.0, and v8.1.0. Do not modify reusable workflow SHAs, OpenCode version/hash, permissions, cron schedule, prompts, or secret names.

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
```

Expected: all tests pass and production statement/branch coverage remains 100%.

- [ ] **Step 5: Commit runtime hardening**

```bash
git add .github/workflows/ci.yml \
  .github/workflows/hourly-commercialization-loop.yml \
  tests/test_publish_workflow.py
git commit -m "ci: move repository actions to Node.js 24 releases"
```

### Task 4: Document setup, provenance boundaries, and release operations

**Files:**
- Create: `docs/releasing.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/research/README.md`
- Test: `tests/test_publish_workflow.py`

**Interfaces:**
- Consumes: the final workflow contract and official PyPI/GitHub/SLSA documentation.
- Produces: exact one-time setup, governed release procedure, verification commands, APA 7 references, and explicit trust boundaries.

- [ ] **Step 1: Create operational release documentation**

Document the exact Trusted Publisher tuple:

```text
PyPI project: rankweave
Owner: ContextualWisdomLab
Repository: RankWeave
Workflow: publish.yml
Environment: pypi
```

Document protected environment setup, version synchronization, GitHub Release tag `v${version}`, publication failure modes, `gh attestation verify dist/* --repo ContextualWisdomLab/RankWeave`, and PyPI attestation verification. State that the external PyPI and GitHub environment setup cannot be completed by repository code.

- [ ] **Step 2: Synchronize architecture and contributor contracts**

Update:

- README installation to prefer PyPI only after the Trusted Publisher has successfully published the version;
- `ARCHITECTURE.md` with build → immutable artifact → provenance → environment-gated OIDC publication;
- `AGENTS.md` and `CLAUDE.md` with release workflow invariants and prohibition on token fallback;
- `CHANGELOG.md` under a new `Unreleased` infrastructure/security section without changing package version.

- [ ] **Step 3: Add APA 7 references**

Add official references for:

```text
Python Packaging Authority. (n.d.). Publishing with a Trusted Publisher. PyPI documentation. Retrieved August 5, 2026, from https://docs.pypi.org/trusted-publishers/using-a-publisher/

Trail of Bits. (2023). PEP 740 – Index support for digital attestations. Python Enhancement Proposals. https://peps.python.org/pep-0740/

GitHub. (n.d.). Using artifact attestations to establish provenance for builds. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Supply-chain Levels for Software Artifacts. (n.d.). Build: Verifying artifacts (SLSA specification v1.2). OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts
```

Explain that attestations establish signed statements about build provenance; they do not prove statistical correctness, absence of vulnerabilities, or downstream policy compliance.

- [ ] **Step 4: Add documentation assertions to workflow tests**

Assert that `docs/releasing.md` contains the exact publisher tuple, version/tag gate, environment protection, GitHub attestation verification, PyPI attestation terminology, and no API-token fallback.

- [ ] **Step 5: Run complete verification**

Run:

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: complete suite passes, production statement/branch coverage is 100%, and both wheel and sdist build.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md ARCHITECTURE.md AGENTS.md CLAUDE.md CHANGELOG.md \
  docs/releasing.md docs/research/README.md tests/test_publish_workflow.py
git commit -m "docs: govern trusted RankWeave releases"
```

## Plan self-review

- **Spec coverage:** release-only trigger, tag/version gate, complete build gate, immutable handoff, GitHub provenance, PyPI OIDC, environment protection, Node.js 24 migration, documentation, and trust boundaries all map to tasks.
- **Placeholder scan:** no TBD, TODO, deferred implementation, or unspecified validation remains.
- **Type and name consistency:** artifact name is always `rankweave-distributions`; environment is always `pypi`; workflow is always `publish.yml`; action SHAs match the design.
- **Scope:** one supply-chain/distribution subsystem; no runtime API, statistical model, database, or UI changes.

## Execution mode

The repository's standing autonomous loop selects inline execution with exact-head review and verification. Every task remains independently reviewable through its tests and commits before the PR is marked ready.
