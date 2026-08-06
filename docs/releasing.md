# Releasing RankWeave

RankWeave publishes immutable wheel and source-distribution artifacts through PyPI Trusted Publishing. The repository stores no PyPI username, password, API token, or alternate-registry fallback.

## Current public-version gap

As of 2026-08-06, the reviewed source tree declares RankWeave `0.18.0`, while
PyPI still exposes only `0.1.0`. Naruon already imports RankWeave through its
hybrid-retrieval seam and therefore cannot consume the audited post-0.1.0 APIs
until a governed public release succeeds. This statement records observed
release state; it is not evidence that `0.18.0` has already been published.

## Release authorization

`.github/workflows/create-release.yml` is the release authorization plane. It
has a bounded bootstrap `push` trigger for the workflow file reaching `main` and
a `workflow_dispatch` input requiring the exact source-tree version. Its
read-only job verifies version identity, exact commit ancestry, absence of the
version from PyPI, absence of the tag and GitHub Release, the full test and 100%
coverage gate, both distribution names, and deterministic CHANGELOG notes.

A separate `contents: write` job, protected by the `pypi` environment, creates
one stable GitHub Release at the exact verified commit. GitHub suppresses most
new workflow runs created by the repository `GITHUB_TOKEN`; a release authored
by that token therefore cannot be trusted to trigger a `release` workflow.
Consequently, a third job with only `actions: write` explicitly invokes the
`workflow_dispatch` interface of `publish.yml` with the exact tag and commit.
No job possesses repository-write, workflow-dispatch, and OIDC publication
permissions together.

`publish.yml` remains the publication plane. It accepts either an externally
published stable GitHub Release event or the explicit governed dispatch. Both
paths must resolve to an existing non-draft, non-prerelease GitHub Release whose
tag points to the exact default-branch commit before the immutable build,
provenance, protected-environment approval, and PyPI Trusted Publishing stages
can run.

For a later release, an authorized operator may start the control plane with:

```bash
gh workflow run create-release.yml   --repo ContextualWisdomLab/RankWeave   --ref main   -f version=${version}
```

The requested version must already be synchronized across the reviewed source
tree; this command never edits version metadata.

## One-time external configuration

The following configuration cannot be completed by repository code alone. A PyPI project owner and a GitHub organization administrator must establish it before the first release.

Configure a pending or normal PyPI Trusted Publisher with this exact identity:

- PyPI project: `rankweave`
- Owner: `ContextualWisdomLab`
- Repository: `RankWeave`
- Workflow: `publish.yml`
- Environment: `pypi`

Create the GitHub environment `pypi` and protect it with required reviewers. Limit deployment branches and tags to the governed release policy. The workflow's publish job requests only `id-token: write`; GitHub's OIDC identity is exchanged for a short-lived PyPI publishing credential.

Do not configure a long-lived package-registry secret as a fallback. A missing Trusted Publisher, environment denial, OIDC failure, or PyPI rejection is a release failure that must be corrected at the source.

## Release preparation

A release commit must synchronize all version-bearing evidence:

- `project.version` in `pyproject.toml`;
- `rankweave.__version__`;
- `EXPECTED_RELEASE_VERSION` in `tests/test_version.py`;
- installed-wheel assertions in CI;
- `CHANGELOG.md` release heading and date;
- user-facing release documentation.

Run the exact quality gate before creating a release:

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

The versioned release tag is exactly `v${version}`. For RankWeave 0.18.0, the only accepted tag is `v0.18.0`. The publishing workflow rejects non-canonical tags, prerelease objects, any mismatch between the release event commit and the checked-out tag, tags whose commit is not reachable from the default branch, and mismatches among the tag, `pyproject.toml`, and the public package version.

## Publication flow

Publishing a GitHub Release triggers `.github/workflows/publish.yml` exactly once per tag.

```text
published stable GitHub Release tag
  -> exact release-event commit on the default-branch history
  -> read-only exact-tag checkout
  -> complete tests and 100% production coverage
  -> wheel and sdist build and archive inspection
  -> immutable rankweave-distributions workflow artifact
  -> GitHub build-provenance attestation
  -> protected pypi environment approval
  -> PyPI Trusted Publishing and PEP 740 attestations
```

The build job has only `contents: read`. The provenance job has `contents: read`, `id-token: write`, and `attestations: write`. The publishing job has only `id-token: write` and receives the immutable distributions after both prior jobs succeed.

The `rankweave-distributions` Actions artifact is retained for seven days for workflow audit and debugging. The workflow does not attach wheel or source-distribution files as GitHub Release assets; PyPI is the durable package-distribution surface.

A failed re-publication is not silently skipped. PyPI versions are immutable; correct the versioning or release process rather than using a skip-existing option.

## Verification after publication

Download the exact wheel and source distribution from PyPI before verifying them. An authorized repository operator may alternatively download the short-lived `rankweave-distributions` artifact from the successful publication workflow run during its retention window. Verify GitHub's build provenance against this repository:

```bash
gh attestation verify path/to/rankweave-0.18.0-py3-none-any.whl \
  --repo ContextualWisdomLab/RankWeave

gh attestation verify path/to/rankweave-0.18.0.tar.gz \
  --repo ContextualWisdomLab/RankWeave
```

Verify PyPI's PEP 740 index-hosted attestations using the verifier currently documented by PyPI and the Python Packaging Authority. The PyPI attestation binds the uploaded distribution digest to the Trusted Publishing identity; GitHub's attestation records the GitHub workflow build provenance. Consumers should verify the exact file they install.

These attestations do not prove that RankWeave is vulnerability-free, statistically correct, appropriate for a particular decision, or compliant with a buyer's policy. They establish signed provenance statements and artifact identity within their respective trust models.

## Failure handling

Treat each condition as a blocker rather than weakening the workflow:

- the GitHub Release is a prerelease;
- the release tag is not canonical;
- the checked-out tag commit differs from the release event commit;
- the released commit is not reachable from the default branch;
- tag and package versions differ;
- tests, coverage, Ruff, or compilation fail;
- wheel or source distribution contents are incomplete;
- immutable artifact upload or digest-checked download fails;
- GitHub provenance cannot be generated;
- the `pypi` environment is not approved;
- PyPI Trusted Publisher identity does not match;
- OIDC exchange or upload fails;
- post-publication attestation verification fails.

Do not delete and recreate a published version. Prepare a new patch version with a complete `CHANGELOG.md` entry and repeat the governed process.
