"""Synchronize RankWeave trusted-release documentation and planning scope."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path_text: str) -> str:
    """Read one repository UTF-8 text file."""
    return (ROOT / path_text).read_text(encoding="utf-8")


def write(path_text: str, content: str) -> None:
    """Write one repository UTF-8 text file with one trailing newline."""
    (ROOT / path_text).write_text(
        content.rstrip("\n") + "\n",
        encoding="utf-8",
    )


def append_once(path_text: str, marker: str, section: str) -> None:
    """Append one section when its stable heading is absent."""
    content = read(path_text)
    if marker not in content:
        write(path_text, content.rstrip() + "\n\n" + section.strip())


def update_changelog() -> None:
    """Record unreleased release-infrastructure and supply-chain changes."""
    path_text = "CHANGELOG.md"
    content = read(path_text)
    if "## [Unreleased]" in content:
        return
    anchor = "## [0.14.0] — 2026-08-05\n"
    if anchor not in content:
        raise SystemExit("missing 0.14.0 changelog anchor")
    section = """## [Unreleased]

### Added
- Release-only PyPI Trusted Publishing with separate build, provenance, and protected publication jobs.
- Immutable wheel and source-distribution handoff plus GitHub build-provenance attestations.
- Governed release operations and post-publication attestation verification guidance.

### Security
- PyPI publication uses GitHub OIDC and the protected `pypi` environment instead of a long-lived registry credential.
- Release tags, package metadata, public version, tests, coverage, wheel resources, and source-distribution contents fail closed before publication.

"""
    write(path_text, content.replace(anchor, section + anchor, 1))


def update_readme() -> None:
    """Document the registry publication state and governed release path."""
    append_once(
        "README.md",
        "## Trusted distribution and provenance",
        """## Trusted distribution and provenance

RankWeave releases are built from the exact published GitHub Release tag, tested at 100% production statement and branch coverage, transferred between jobs as one immutable distribution artifact, and published through PyPI Trusted Publishing after the protected `pypi` environment approves the deployment.

After a version has been published and independently verified, install it from PyPI:

```bash
python -m pip install rankweave==0.14.0
```

Before the first Trusted Publisher is configured or when a version has not been published, use a reviewed source checkout instead of assuming that the PyPI name is owned by this project. See [`docs/releasing.md`](docs/releasing.md) for the exact publisher identity, release procedure, and GitHub/PyPI attestation verification boundaries.""",
    )


def update_architecture() -> None:
    """Document the split release and provenance boundary."""
    append_once(
        "ARCHITECTURE.md",
        "## Governed release boundary",
        """## Governed release boundary

A published GitHub Release is the only publication trigger. A read-only exact-tag build job verifies tag and package version identity, runs the complete quality gate, builds one wheel and one source distribution, and uploads one immutable Actions artifact. Separate jobs download that artifact with digest mismatch configured to fail: the provenance job creates GitHub build-provenance attestations, and the protected `pypi` environment job exchanges GitHub OIDC for a short-lived PyPI publishing credential.

The repository stores no package-registry credential and provides no token fallback. GitHub and PyPI attestations bind signed statements to exact artifact digests; they do not establish statistical validity, vulnerability absence, or downstream policy compliance.""",
    )


def update_agent_contracts() -> None:
    """Record release invariants for future automated contributors."""
    append_once(
        "AGENTS.md",
        "## Trusted release gate",
        """## Trusted release gate

Do not publish from a branch, pull request, manual workflow dispatch, reusable workflow, or stored PyPI credential. A release change must preserve the exact `v${version}` tag gate, frozen full tests and 100% coverage before build, one wheel plus one sdist inspection, immutable artifact handoff, GitHub provenance, protected `pypi` environment, PyPI OIDC, full-SHA action pins, and post-publication verification. Never add `skip-existing` or an alternate registry fallback to make a failed release appear successful.""",
    )
    append_once(
        "CLAUDE.md",
        "## Release workflow",
        """## Release workflow

`.github/workflows/publish.yml` is a security-sensitive distribution boundary. Keep build, provenance, and publication in separate least-privilege jobs. Publication is release-only, environment-gated, tokenless, and fail-closed. Version-bearing files, CHANGELOG, archive contents, action SHAs, and attestation documentation must change together. A provenance attestation is not a claim of package correctness or scientific validity.""",
    )


def update_research_references() -> None:
    """Add APA 7 references for tokenless publishing and attestations."""
    append_once(
        "docs/research/README.md",
        "### Trusted publishing and release provenance",
        """### Trusted publishing and release provenance

GitHub. (n.d.). *Using artifact attestations to establish provenance for builds*. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Python Packaging Authority. (n.d.). *Publishing with a Trusted Publisher*. PyPI documentation. Retrieved August 5, 2026, from https://docs.pypi.org/trusted-publishers/using-a-publisher/

Trail of Bits. (2023). PEP 740—Index support for digital attestations. *Python Enhancement Proposals*. https://peps.python.org/pep-0740/

Supply-chain Levels for Software Artifacts. (n.d.). *Build: Verifying artifacts (SLSA specification v1.2)*. OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts

PyPI Trusted Publishing exchanges a GitHub OIDC identity for a short-lived publication credential and avoids storing a registry token. PEP 740 index-hosted attestations and GitHub Artifact Attestations bind signed statements to artifact digests in distinct trust systems. Neither proves that retrieval statistics are scientifically valid, that the package is vulnerability-free, or that a buyer's deployment policy has been satisfied.""",
    )


def narrow_design_scope() -> None:
    """Remove a separate Node.js migration from this bounded release slice."""
    path_text = (
        "docs/superpowers/specs/"
        "2026-08-05-trusted-pypi-release-design.md"
    )
    content = read(path_text)
    section_start = content.find("## Repository action-runtime hardening\n")
    if section_start != -1:
        section_end = content.find("## Tests\n", section_start)
        if section_end == -1:
            raise SystemExit("missing design tests section")
        content = content[:section_start] + content[section_end:]
    content = content.replace(
        "- no `COPILOT_GITHUB_TOKEN` appears;\n"
        "- CI and hourly workflow action references are Node.js 24-compatible "
        "pinned releases.\n",
        "- no `COPILOT_GITHUB_TOKEN` appears.\n",
    )
    write(path_text, content)


def narrow_plan_scope() -> None:
    """Keep the implementation plan limited to release distribution."""
    path_text = (
        "docs/superpowers/plans/"
        "2026-08-05-trusted-pypi-release.md"
    )
    content = read(path_text)
    content = content.replace(
        " and move repository-owned JavaScript actions to pinned Node.js "
        "24-compatible releases",
        "",
        1,
    )
    task_start = content.find(
        "### Task 3: Migrate repository-owned actions to Node.js 24 releases\n"
    )
    task_end = content.find(
        "### Task 4: Document setup, provenance boundaries, and release "
        "operations\n"
    )
    if task_start != -1:
        if task_end == -1:
            raise SystemExit("missing release documentation task")
        replacement_heading = (
            "### Task 3: Document setup, provenance boundaries, and release "
            "operations\n"
        )
        content = content[:task_start] + replacement_heading + content[
            task_end
            + len(
                "### Task 4: Document setup, provenance boundaries, and "
                "release operations\n"
            ) :
        ]
    content = content.replace(
        "Node.js 24 migration, ",
        "",
    )
    content = content.replace(
        "- Existing NVIDIA/OpenCode autonomous workflow secrets and central "
        "reusable-workflow SHAs are unchanged.\n",
        "- Existing CI, hourly automation, NVIDIA/OpenCode secrets, and "
        "central reusable-workflow SHAs are unchanged.\n",
    )
    write(path_text, content)


def main() -> None:
    """Apply all documentation and planning updates."""
    update_changelog()
    update_readme()
    update_architecture()
    update_agent_contracts()
    update_research_references()
    narrow_design_scope()
    narrow_plan_scope()


if __name__ == "__main__":
    main()
