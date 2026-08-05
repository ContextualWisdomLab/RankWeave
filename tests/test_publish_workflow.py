import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SHA_ACTION_PATTERN = re.compile(
    r"uses:\s+([^\s@]+)@([0-9a-f]{40})(?:\s|$)"
)
EXTERNAL_USES_PATTERN = re.compile(r"uses:\s+([^\s]+)")

CHECKOUT_SHA = "de0fac2e4500dabe0009e67214ff5f5447ce83dd"
SETUP_PYTHON_SHA = "a309ff8b426b58ec0e2a45f0f869d46889d02405"
SETUP_UV_SHA = "08807647e7069bb48b6ef5acd8ec9567f424441b"
UPLOAD_ARTIFACT_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
DOWNLOAD_ARTIFACT_SHA = "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
ATTEST_SHA = "1e69f48acb82d1966a394da916b4c1698aa569d6"
PYPI_PUBLISH_SHA = "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"

EXPECTED_PUBLISH_ACTIONS = {
    "actions/checkout": CHECKOUT_SHA,
    "actions/setup-python": SETUP_PYTHON_SHA,
    "astral-sh/setup-uv": SETUP_UV_SHA,
    "actions/upload-artifact": UPLOAD_ARTIFACT_SHA,
    "actions/download-artifact": DOWNLOAD_ARTIFACT_SHA,
    "actions/attest": ATTEST_SHA,
    "pypa/gh-action-pypi-publish": PYPI_PUBLISH_SHA,
}


def _read_repository_file(path_text: str) -> str:
    return (REPOSITORY_ROOT / path_text).read_text(encoding="utf-8")


def _publish_workflow() -> str:
    return _read_repository_file(".github/workflows/publish.yml")


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


def test_publish_workflow_is_release_published_only():
    workflow_text = _publish_workflow()

    trigger_block = workflow_text.split("permissions:", 1)[0]
    assert "on:\n  release:\n    types: [published]\n" in trigger_block
    assert "workflow_dispatch:" not in trigger_block
    assert "workflow_call:" not in trigger_block
    assert "pull_request:" not in trigger_block
    assert "push:" not in trigger_block
    assert "schedule:" not in trigger_block
    assert "cancel-in-progress: false" in workflow_text


def test_publish_workflow_pins_exact_current_actions():
    workflow_text = _publish_workflow()

    references = _action_references(workflow_text)
    assert set(references) == set(EXPECTED_PUBLISH_ACTIONS.items())
    assert len(references) == 8


def test_publish_workflow_separates_jobs_and_handoffs_one_artifact():
    workflow_text = _publish_workflow()
    build_block = _job_block(workflow_text, "build", "provenance")
    provenance_block = _job_block(workflow_text, "provenance", "publish")
    publish_block = _job_block(workflow_text, "publish", None)

    assert "needs:" not in build_block
    assert "needs: build" in provenance_block
    assert "needs: [build, provenance]" in publish_block
    assert build_block.index("python -m coverage run -m pytest -q") < (
        build_block.index("uv build --wheel --sdist --out-dir dist")
    )
    assert "name: rankweave-distributions" in build_block
    assert (
        "path: |\n"
        "            dist/\n"
        "            release-handoff/SHA256SUMS"
    ) in build_block
    assert "if-no-files-found: error" in build_block
    assert "include-hidden-files: false" in build_block
    assert "retention-days: 7" in build_block
    assert "name: rankweave-distributions" in provenance_block
    assert "path: handoff/" in provenance_block
    assert "name: rankweave-distributions" in publish_block
    assert "path: handoff/" in publish_block
    assert "digest-mismatch:" not in workflow_text


def test_distribution_handoff_is_checksum_verified_before_use():
    workflow_text = _publish_workflow()
    build_block = _job_block(workflow_text, "build", "provenance")
    provenance_block = _job_block(workflow_text, "provenance", "publish")
    publish_block = _job_block(workflow_text, "publish", None)

    assert (
        "manifest_sha256: ${{ steps.distributions.outputs.manifest_sha256 }}"
        in build_block
    )
    assert ") > release-handoff/SHA256SUMS" in build_block
    assert "sha256sum release-handoff/SHA256SUMS" in build_block
    assert "manifest_sha256=%s" in build_block
    for job_block in (provenance_block, publish_block):
        assert "Verify immutable distribution handoff" in job_block
        assert (
            "EXPECTED_MANIFEST_SHA256: "
            "${{ needs.build.outputs.manifest_sha256 }}"
        ) in job_block
        assert "handoff/release-handoff/SHA256SUMS" in job_block
        assert "sha256sum --check --strict -" in job_block
        assert "cd handoff/dist" in job_block
        assert (
            "sha256sum --check --strict ../release-handoff/SHA256SUMS"
            in job_block
        )
    assert "handoff/dist/*.whl" in provenance_block
    assert "handoff/dist/*.tar.gz" in provenance_block
    assert "packages-dir: handoff/dist/" in publish_block
    assert "packages-dir: dist/" not in publish_block


def test_build_job_checks_exact_release_identity_and_default_branch_reachability():
    build_block = _job_block(_publish_workflow(), "build", "provenance")

    assert "ref: ${{ github.event.release.tag_name }}" in build_block
    assert "fetch-depth: 0" in build_block
    assert "persist-credentials: false" in build_block
    assert "DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}" in (
        build_block
    )
    assert "RELEASE_PRERELEASE: ${{ github.event.release.prerelease }}" in (
        build_block
    )
    assert "RELEASE_SHA: ${{ github.sha }}" in build_block
    assert "RELEASE_TAG: ${{ github.event.release.tag_name }}" in build_block
    assert "release tag is not canonical" in build_block
    assert "stable package publication rejects prereleases" in build_block
    assert "checked-out commit" in build_block
    assert "release event commit" in build_block
    assert '"merge-base",' in build_block
    assert '"--is-ancestor",' in build_block
    assert "released commit must be reachable from the default branch" in (
        build_block
    )


def test_build_job_checks_package_version_and_complete_quality_gate():
    build_block = _job_block(_publish_workflow(), "build", "provenance")

    assert 'release_tag != f"v{version}"' in build_block
    assert "rankweave.__version__" in build_block
    assert "uv sync --frozen --extra dev --python 3.13" in build_block
    assert "python -m compileall -q src" in build_block
    assert "python -m ruff check ." in build_block
    assert "python -m coverage run -m pytest -q" in build_block
    assert "python -m coverage report" in build_block
    assert "uv build --wheel --sdist --out-dir dist" in build_block
    assert "release must contain exactly one wheel and one " in build_block
    assert '"source distribution"' in build_block
    assert "rankweave/schemas/artifact-verification-v1.schema.json" in build_block
    assert "CHANGELOG.md" in build_block


def test_release_jobs_use_least_privilege_and_protected_environment():
    workflow_text = _publish_workflow()
    build_block = _job_block(workflow_text, "build", "provenance")
    provenance_block = _job_block(workflow_text, "provenance", "publish")
    publish_block = _job_block(workflow_text, "publish", None)

    assert "permissions: {}" in workflow_text
    assert "permissions:\n      contents: read\n" in build_block
    assert (
        "permissions:\n"
        "      contents: read\n"
        "      id-token: write\n"
        "      attestations: write\n"
        "      artifact-metadata: write\n"
    ) in provenance_block
    assert "permissions:\n      id-token: write\n" in publish_block
    assert "contents: write" not in workflow_text
    assert "packages: write" not in workflow_text
    assert "pull-requests: write" not in workflow_text
    assert "environment:\n      name: pypi\n" in publish_block
    assert "url: https://pypi.org/p/rankweave" in publish_block


def test_publish_job_has_no_registry_secret_or_fallback():
    workflow_text = _publish_workflow()
    publish_block = _job_block(workflow_text, "publish", None)
    forbidden_fragments = (
        "PYPI_API_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "password:",
        "user:",
        "username:",
        "repository-url:",
        "repository_url:",
        "skip-existing:",
        "skip_existing:",
        "secrets.",
    )

    for fragment in forbidden_fragments:
        assert fragment not in publish_block
    assert (
        f"uses: pypa/gh-action-pypi-publish@{PYPI_PUBLISH_SHA}"
        in publish_block
    )


def test_release_documentation_records_exact_external_setup_and_boundaries():
    documentation = _read_repository_file("docs/releasing.md")

    for expected in (
        "PyPI project: `rankweave`",
        "Owner: `ContextualWisdomLab`",
        "Repository: `RankWeave`",
        "Workflow: `publish.yml`",
        "Environment: `pypi`",
        "v${version}",
        "gh attestation verify",
        "PEP 740",
        "required reviewers",
        "cannot be completed by repository code alone",
    ):
        assert expected in documentation
    assert "PYPI_API_TOKEN" not in documentation
    assert "stored API token" not in documentation


def test_normal_package_ci_builds_and_inspects_source_distribution():
    ci_workflow = _read_repository_file(".github/workflows/ci.yml")

    assert "uv build --wheel --sdist --out-dir dist" in ci_workflow
    assert "Verify source distribution contents" in ci_workflow
    assert "package job requires exactly one source distribution" in ci_workflow
    assert 'source_root + "CHANGELOG.md"' in ci_workflow
    assert 'source_root + "tests/test_version.py"' in ci_workflow
