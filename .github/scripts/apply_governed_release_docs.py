"""Apply the reviewed governed-release documentation changes exactly once."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path_text: str) -> str:
    """Read one repository file as UTF-8."""
    return (ROOT / path_text).read_text(encoding="utf-8")


def write(path_text: str, content: str) -> None:
    """Write one repository file as UTF-8."""
    (ROOT / path_text).write_text(content, encoding="utf-8")


def replace_exact(path_text: str, old: str, new: str) -> None:
    """Replace one exact block and fail on unexpected repository state."""
    content = read(path_text)
    if content.count(old) != 1:
        raise SystemExit(
            f"{path_text}: expected exactly one replacement block"
        )
    write(path_text, content.replace(old, new, 1))


def insert_before(path_text: str, marker: str, addition: str) -> None:
    """Insert an idempotent block before one exact marker."""
    content = read(path_text)
    if addition.strip() in content:
        return
    if content.count(marker) != 1:
        raise SystemExit(f"{path_text}: expected one marker {marker!r}")
    write(path_text, content.replace(marker, addition + marker, 1))


RELEASE_DOC_SECTION = """## Current public-version gap

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
gh workflow run create-release.yml \
  --repo ContextualWisdomLab/RankWeave \
  --ref main \
  -f version=${version}
```

The requested version must already be synchronized across the reviewed source
tree; this command never edits version metadata.

"""
insert_before(
    "docs/releasing.md",
    "## One-time external configuration\n",
    RELEASE_DOC_SECTION,
)

OLD_AGENT_PARITY = """- **Behavior parity with naruon.** A behavior change in shared retrieval
  primitives must be mirrored in naruon's `services/hybrid_retrieval` until
  naruon consumes this package directly. Prefer additive, backward-compatible
  changes.
"""
NEW_AGENT_PARITY = """- **Consumer-version parity with naruon.** Naruon already imports this package
  through `services.hybrid_retrieval`. A public RankWeave release and the naruon
  version/hash-lock upgrade remain separate reviewed changes; never claim that
  a source-only API is available to naruon while its public package pin is old.
  Prefer additive, backward-compatible changes.
"""
replace_exact("AGENTS.md", OLD_AGENT_PARITY, NEW_AGENT_PARITY)

OLD_AGENT_RELEASE = """## Trusted release gate

Do not publish from a branch, pull request, manual workflow dispatch, reusable workflow, or stored PyPI credential. A release change must preserve the exact `v${version}` tag gate, frozen full tests and 100% coverage before build, one wheel plus one sdist inspection, immutable artifact handoff, GitHub provenance, protected `pypi` environment, PyPI OIDC, full-SHA action pins, and post-publication verification. Never add `skip-existing` or an alternate registry fallback to make a failed release appear successful.
"""
NEW_AGENT_RELEASE = """## Trusted release gate

`create-release.yml` authorizes one exact stable GitHub Release after source,
version, ancestry, duplicate-state, tests, 100% coverage, and distribution-name
checks. It separates `contents: write` release creation from an `actions: write`
`workflow_dispatch` of `publish.yml`, because ordinary events created with the
repository `GITHUB_TOKEN` do not start another workflow. `publish.yml` must then
revalidate the existing stable release and exact tag commit before immutable
artifact handoff, GitHub provenance, protected `pypi` environment approval, and
PyPI OIDC publication. Never add a stored package credential, force tag
movement, `skip-existing`, or an alternate registry fallback.
"""
replace_exact("AGENTS.md", OLD_AGENT_RELEASE, NEW_AGENT_RELEASE)

insert_before(
    "AGENTS.md",
    "- `.github/workflows/hourly-commercialization-loop.yml`",
    "- `.github/workflows/create-release.yml` — governed stable-release "
    "authorization and explicit publisher dispatch.\n"
    "- `.github/workflows/publish.yml` — exact-release build, provenance, "
    "and PyPI Trusted Publishing.\n",
)

OLD_CLAUDE_RELEASE = """## Release workflow

`.github/workflows/publish.yml` is a security-sensitive distribution boundary. Keep build, provenance, and publication in separate least-privilege jobs. Publication is release-only, environment-gated, tokenless, and fail-closed. Version-bearing files, CHANGELOG, archive contents, action SHAs, and attestation documentation must change together. A provenance attestation is not a claim of package correctness or scientific validity.
"""
NEW_CLAUDE_RELEASE = """## Release workflow

`.github/workflows/create-release.yml` is the release-authorization boundary:
verify read-only, create the stable GitHub Release with `contents: write`, then
explicitly dispatch the publisher with an isolated `actions: write` job.
`.github/workflows/publish.yml` accepts only a stable release event or that
exact-tag/exact-SHA `workflow_dispatch`, revalidates the GitHub Release, and
keeps build, provenance, and OIDC publication in separate least-privilege jobs.
Do not add a stored registry or GitHub credential. Version-bearing files,
CHANGELOG, archive contents, action SHAs, and attestation documentation change
together. Provenance does not prove package correctness or scientific validity.
"""
replace_exact("CLAUDE.md", OLD_CLAUDE_RELEASE, NEW_CLAUDE_RELEASE)

architecture = read("ARCHITECTURE.md")
heading = "## Governed release boundary\n"
if architecture.count(heading) != 1:
    raise SystemExit("ARCHITECTURE.md: governed release heading mismatch")
architecture_prefix = architecture.split(heading, 1)[0]
NEW_ARCHITECTURE_RELEASE = """## Governed release boundary

Release authorization and package publication are different trust domains.
`create-release.yml` first verifies the exact default-branch commit, synchronized
0.18.0 identity, missing public PyPI version, missing tag and release, full tests,
100% statement/branch coverage, distribution names, and deterministic CHANGELOG
notes with `contents: read` only.

The protected `pypi` environment release job receives only `contents: write` and
creates a stable GitHub Release targeted at that verified SHA. Because GitHub
suppresses ordinary workflow events generated with the repository
`GITHUB_TOKEN`, a distinct job with only `actions: write` starts the explicit
`workflow_dispatch` interface of `publish.yml`. This avoids a personal access
token or GitHub App private key while keeping release and dispatch authority
separate.

`publish.yml` independently accepts an external stable release event or the
explicit tag/SHA dispatch. Its read-only build job verifies the existing GitHub
Release, tag-to-commit identity, default-branch reachability, package version,
complete quality gate, and wheel/source contents. It records a SHA-256 manifest
and uploads both distributions plus that manifest as one immutable Actions
artifact.

Separate provenance and publication jobs verify the handoff before use. The
provenance job creates GitHub build-provenance attestations. The protected
`pypi` job exchanges GitHub OIDC for a short-lived PyPI Trusted Publishing
credential. No long-lived registry credential, force-moving tag,
`skip-existing`, or alternate registry exists. GitHub and PyPI attestations bind
statements to artifact digests; they do not establish statistical validity,
vulnerability absence, or downstream policy compliance.
"""
write("ARCHITECTURE.md", architecture_prefix + NEW_ARCHITECTURE_RELEASE)

CHANGELOG_RELEASE = """### Release operations
- Added a permanent least-privilege `create-release.yml` authorization workflow
  for exact stable releases, with bounded bootstrap and manual invocation.
- Added an explicit exact-tag/exact-SHA `workflow_dispatch` publisher path so a
  GitHub Release created with `GITHUB_TOKEN` cannot leave PyPI silently stale.
- Preserved separate immutable build, GitHub provenance, protected `pypi`
  environment, OIDC Trusted Publishing, and post-publication verification.

"""
insert_before("CHANGELOG.md", "### Validation\n", CHANGELOG_RELEASE)

replace_exact(
    "docs/superpowers/specs/2026-08-06-governed-release-publication-design.md",
    """The repository already contains a release-event publishing workflow that builds, tests, attests, and uploads distributions through PyPI Trusted Publishing. The missing product boundary is a governed way to create the exact stable GitHub Release that starts that workflow.
""",
    """The repository already contains a publishing workflow that builds, tests, attests, and uploads distributions through PyPI Trusted Publishing. The missing product boundary is a governed way to create the exact stable GitHub Release and explicitly dispatch publication: GitHub does not start an ordinary release-event workflow for a Release created with the repository `GITHUB_TOKEN`.
""",
)
replace_exact(
    "docs/superpowers/specs/2026-08-06-governed-release-publication-design.md",
    """The workflow has a read-only `verify` job followed by a `release` job. The release job is bound to the existing `pypi` environment and receives only `contents: write`. It creates a stable GitHub Release with tag `v${version}` targeted at the exact verified commit.

This approach is preferred over a one-off script because it leaves a reusable, reviewable release control plane. It is preferred over extending `publish.yml` because separating release authorization from artifact publication reduces privilege concentration and keeps the publish workflow release-event-only.
""",
    """The workflow has a read-only `verify` job followed by a protected `release` job with only `contents: write`. A third job with only `actions: write` invokes the exact-tag/exact-SHA `workflow_dispatch` interface of `publish.yml`. The publisher independently verifies the existing stable GitHub Release before build, provenance, and OIDC upload.

This approach leaves a reusable, reviewable release control plane without a personal access token or GitHub App private key. It separates release mutation, workflow dispatch, build provenance, and package publication so no job receives all authorities.
""",
)
replace_exact(
    "docs/superpowers/specs/2026-08-06-governed-release-publication-design.md",
    """    E --> R[Stable GitHub Release v0.18.0]
    R --> P[Existing publish.yml]
""",
    """    E --> R[Stable GitHub Release v0.18.0]
    R --> D[Explicit workflow_dispatch]
    D --> P[Existing publish.yml]
""",
)
replace_exact(
    "docs/superpowers/specs/2026-08-06-governed-release-publication-design.md",
    """A queued environment approval is not treated as success. A missing Trusted Publisher, environment denial, OIDC failure, PyPI conflict, or attestation failure remains visible in the existing publication workflow and must be corrected without weakening the contract. If the GitHub Release succeeds but publication fails, the same version is not recreated; the failed publication is repaired at its configuration or workflow source and rerun only through the governed release-event mechanism where GitHub permits it, otherwise a new patch version is prepared.
""",
    """A queued environment approval is not treated as success. A missing Trusted Publisher, environment denial, explicit dispatch failure, OIDC failure, PyPI conflict, or attestation failure remains visible and must be corrected without weakening the contract. If the GitHub Release succeeds but publication fails, the same version is not recreated; publication may be re-dispatched only after the exact stable release and source remain valid, otherwise a new patch version is prepared.
""",
)

replace_exact(
    "docs/superpowers/plans/2026-08-06-governed-release-publication.md",
    """**Architecture:** A read-only verification job validates the exact source commit, version identity, release uniqueness, PyPI absence, and complete package quality gate. A separate `contents: write` job, protected by the existing `pypi` environment, creates one stable GitHub Release; the existing release-event `publish.yml` remains the only artifact builder, attestor, and PyPI publisher.
""",
    """**Architecture:** A read-only verification job validates the exact source commit, version identity, release uniqueness, PyPI absence, and complete package quality gate. A protected `contents: write` job creates one stable GitHub Release, and an isolated `actions: write` job explicitly dispatches `publish.yml` with the exact tag and SHA because `GITHUB_TOKEN`-created release events do not start another workflow. `publish.yml` remains the only artifact builder, attestor, and PyPI publisher.
""",
)
replace_exact(
    "docs/superpowers/plans/2026-08-06-governed-release-publication.md",
    """- Produces: a `Create RankWeave Release` workflow with manual and bounded bootstrap triggers.
""",
    """- Produces: a `Create RankWeave Release` workflow with manual and bounded bootstrap triggers plus explicit least-privilege publication dispatch.
""",
)
