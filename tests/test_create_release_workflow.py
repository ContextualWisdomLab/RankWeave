import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ".github/workflows/create-release.yml"

SHA_ACTION_PATTERN = re.compile(
    r"uses:\s+([^\s@]+)@([0-9a-f]{40})(?:\s|$)"
)
EXTERNAL_USES_PATTERN = re.compile(r"uses:\s+([^\s]+)")

CHECKOUT_SHA = "de0fac2e4500dabe0009e67214ff5f5447ce83dd"
SETUP_PYTHON_SHA = "a309ff8b426b58ec0e2a45f0f869d46889d02405"
SETUP_UV_SHA = "08807647e7069bb48b6ef5acd8ec9567f424441b"
UPLOAD_ARTIFACT_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
DOWNLOAD_ARTIFACT_SHA = "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"

EXPECTED_ACTIONS = {
    "actions/checkout": CHECKOUT_SHA,
    "actions/setup-python": SETUP_PYTHON_SHA,
    "astral-sh/setup-uv": SETUP_UV_SHA,
    "actions/upload-artifact": UPLOAD_ARTIFACT_SHA,
    "actions/download-artifact": DOWNLOAD_ARTIFACT_SHA,
}


def _read_repository_file(path_text: str) -> str:
    return (REPOSITORY_ROOT / path_text).read_text(encoding="utf-8")


def _release_workflow() -> str:
    return _read_repository_file(WORKFLOW_PATH)


def _job_block(workflow_text: str, job_name: str, next_job_name: str | None) -> str:
    start_marker = f"  {job_name}:\n"
    start = workflow_text.index(start_marker)
    if next_job_name is None:
        return workflow_text[start:]
    end_marker = f"  {next_job_name}:\n"
    end = workflow_text.index(end_marker, start + len(start_marker))
    return workflow_text[start:end]


def _action_references(workflow_text: str) -> tuple[tuple[str, str], ...]:
    references = SHA_ACTION_PATTERN.findall(workflow_text)
    all_uses = EXTERNAL_USES_PATTERN.findall(workflow_text)
    assert len(references) == len(all_uses)
    return tuple(references)


def test_release_creation_has_manual_and_bounded_bootstrap_triggers():
    workflow_text = _release_workflow()
    trigger_block = workflow_text.split("permissions:", 1)[0]

    assert "on:\n  workflow_dispatch:\n" in trigger_block
    assert "version:\n" in trigger_block
    assert "required: true" in trigger_block
    assert "type: string" in trigger_block
    assert "  push:\n    branches: [main]\n" in trigger_block
    assert (
        "paths:\n      - .github/workflows/create-release.yml" in trigger_block
    )
    assert "schedule:" not in trigger_block
    assert "pull_request:" not in trigger_block
    assert "workflow_call:" not in trigger_block
    assert "cancel-in-progress: false" in workflow_text


def test_release_creation_pins_exact_current_actions():
    references = _action_references(_release_workflow())

    assert set(references) == set(EXPECTED_ACTIONS.items())
    assert len(references) == 5


def test_release_creation_separates_verification_release_and_dispatch():
    workflow_text = _release_workflow()
    verify_block = _job_block(workflow_text, "verify", "release")
    release_block = _job_block(workflow_text, "release", "publish_dispatch")
    dispatch_block = _job_block(workflow_text, "publish_dispatch", None)

    assert "permissions: {}" in workflow_text
    assert "permissions:\n      contents: read\n" in verify_block
    assert "contents: write" not in verify_block
    assert "actions: write" not in verify_block
    assert "needs: verify" in release_block
    assert "permissions:\n      contents: write\n" in release_block
    assert "actions: write" not in release_block
    assert "needs: [verify, release]" in dispatch_block
    assert "permissions:\n      actions: write\n" in dispatch_block
    assert "contents: write" not in dispatch_block
    assert "id-token: write" not in workflow_text
    assert "packages: write" not in workflow_text
    assert "pull-requests: write" not in workflow_text
    assert "environment:\n      name: pypi\n" in release_block
    assert "gh release create" not in verify_block
    assert "gh release create" in release_block
    assert "gh workflow run publish.yml" in dispatch_block


def test_verify_job_checks_exact_version_commit_and_default_branch():
    verify_block = _job_block(_release_workflow(), "verify", "release")

    for expected in (
        "REQUESTED_VERSION",
        "EVENT_NAME",
        "EVENT_SHA",
        "DEFAULT_BRANCH",
        "SOURCE_VERSION",
        "release version must match",
        "source version",
        "rankweave.__version__",
        "EXPECTED_RELEASE_VERSION",
        "CHANGELOG.md",
        "git rev-parse HEAD",
        "git merge-base --is-ancestor",
        "must be reachable from origin/",
        "release_version=",
        "release_tag=",
        "verified_sha=",
    ):
        assert expected in verify_block
    assert "ref: ${{ github.sha }}" in verify_block
    assert "fetch-depth: 0" in verify_block
    assert "persist-credentials: false" in verify_block
    assert "[0-9]+\\.[0-9]+\\.[0-9]+" in verify_block


def test_verify_job_rejects_existing_pypi_tag_and_release_state():
    verify_block = _job_block(_release_workflow(), "verify", "release")

    assert "https://pypi.org/pypi/rankweave/${version}/json" in verify_block
    assert "PyPI version already exists" in verify_block
    assert "unexpected PyPI response" in verify_block
    assert "/git/ref/tags/${encoded_tag}" in verify_block
    assert "/releases/tags/${encoded_tag}" in verify_block
    assert "Git tag already exists" in verify_block
    assert "GitHub Release already exists" in verify_block
    assert "unexpected GitHub API response" in verify_block
    assert "Authorization: Bearer ${GH_TOKEN}" in verify_block


def test_verify_job_runs_complete_quality_gate_before_build_handoff():
    verify_block = _job_block(_release_workflow(), "verify", "release")

    commands = (
        "uv sync --frozen --extra dev --python 3.13",
        "python -m compileall -q src",
        "python -m ruff check .",
        "python -m coverage run -m pytest -q",
        "python -m coverage report",
        "uv build --wheel --sdist --out-dir dist",
    )
    positions = tuple(verify_block.index(command) for command in commands)
    assert positions == tuple(sorted(positions))
    assert "exactly one wheel and one source distribution" in verify_block
    assert "rankweave-${version}-py3-none-any.whl" in verify_block
    assert "rankweave-${version}.tar.gz" in verify_block
    assert "Extract deterministic release notes" in verify_block
    assert "## [${version}]" in verify_block
    assert "name: rankweave-release-notes" in verify_block
    assert "path: release-handoff/RELEASE_NOTES.md" in verify_block
    assert "if-no-files-found: error" in verify_block
    assert "include-hidden-files: false" in verify_block
    assert "retention-days: 1" in verify_block


def test_release_job_rechecks_state_and_targets_verified_sha():
    release_block = _job_block(
        _release_workflow(), "release", "publish_dispatch"
    )

    for expected in (
        "name: rankweave-release-notes",
        "path: release-handoff/",
        "RELEASE_VERSION: ${{ needs.verify.outputs.release_version }}",
        "RELEASE_TAG: ${{ needs.verify.outputs.release_tag }}",
        "VERIFIED_SHA: ${{ needs.verify.outputs.verified_sha }}",
        "/git/ref/tags/${encoded_tag}",
        "/releases/tags/${encoded_tag}",
        "gh release create \"$RELEASE_TAG\"",
        "--repo \"$GITHUB_REPOSITORY\"",
        "--target \"$VERIFIED_SHA\"",
        "--title \"RankWeave $RELEASE_VERSION\"",
        "--notes-file release-handoff/RELEASE_NOTES.md",
        "GH_TOKEN: ${{ github.token }}",
    ):
        assert expected in release_block
    assert "--draft" not in release_block
    assert "--prerelease" not in release_block
    assert "--generate-notes" not in release_block


def test_dispatch_job_explicitly_starts_the_publisher():
    dispatch_block = _job_block(
        _release_workflow(), "publish_dispatch", None
    )

    for expected in (
        "RELEASE_TAG: ${{ needs.verify.outputs.release_tag }}",
        "VERIFIED_SHA: ${{ needs.verify.outputs.verified_sha }}",
        "GH_TOKEN: ${{ github.token }}",
        "gh workflow run publish.yml",
        "--ref main",
        "-f release_tag=\"$RELEASE_TAG\"",
        "-f release_sha=\"$VERIFIED_SHA\"",
    ):
        assert expected in dispatch_block


def test_publish_workflow_accepts_release_and_explicit_dispatch_only():
    publish_workflow = _read_repository_file(".github/workflows/publish.yml")
    trigger_block = publish_workflow.split("permissions:", 1)[0]

    assert "release:\n    types: [published]" in trigger_block
    assert "workflow_dispatch:" in trigger_block
    assert "release_tag:" in trigger_block
    assert "release_sha:" in trigger_block
    assert "required: true" in trigger_block
    assert "pull_request:" not in trigger_block
    assert "push:" not in trigger_block
    assert "schedule:" not in trigger_block
    assert "EVENT_NAME" in publish_workflow
    assert "DISPATCH_RELEASE_TAG" in publish_workflow
    assert "DISPATCH_RELEASE_SHA" in publish_workflow
    assert "stable GitHub Release" in publish_workflow


def test_release_creation_contains_no_long_lived_credential_or_fallback():
    workflow_text = _release_workflow()
    forbidden_fragments = (
        "PYPI_API_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "password:",
        "username:",
        "repository-url:",
        "repository_url:",
        "skip-existing",
        "skip_existing",
        "--force",
        "secrets.",
        "test.pypi.org",
    )

    for fragment in forbidden_fragments:
        assert fragment not in workflow_text


def test_release_documentation_records_authorization_publication_boundary():
    documentation = _read_repository_file("docs/releasing.md")
    architecture = _read_repository_file("ARCHITECTURE.md")
    agents = _read_repository_file("AGENTS.md")
    claude = _read_repository_file("CLAUDE.md")
    changelog = _read_repository_file("CHANGELOG.md")
    adr = _read_repository_file(
        "docs/adr/0004-separate-release-authorization-from-publication.md"
    )

    for expected in (
        "create-release.yml",
        "release authorization",
        "publish.yml",
        "PyPI still exposes only `0.1.0`",
        "workflow_dispatch",
        "pypi",
        "v0.18.0",
        "GITHUB_TOKEN",
    ):
        assert expected in documentation
    assert "release authorization" in architecture.lower()
    assert "create-release.yml" in agents
    assert "create-release.yml" in claude
    assert "Release operations" in changelog
    assert "Status: Accepted" in adr
    assert "PyPI Trusted Publishing" in adr
    assert "SLSA v1.2" in adr
    assert "workflow_dispatch" in adr
