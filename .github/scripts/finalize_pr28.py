"""Finalize trusted-release validation and remove stale planning language."""

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


def replace_once(path_text: str, old: str, new: str, label: str) -> None:
    """Replace one exact fragment and fail closed when the source drifts."""
    content = read(path_text)
    if old not in content:
        raise SystemExit(f"missing {label} anchor in {path_text}")
    write(path_text, content.replace(old, new, 1))


def update_ci_source_distribution_gate() -> None:
    """Build and inspect the source distribution on every package CI run."""
    path_text = ".github/workflows/ci.yml"
    content = read(path_text)
    content = content.replace(
        "      - run: uv build --wheel --out-dir dist\n",
        "      - run: uv build --wheel --sdist --out-dir dist\n",
        1,
    )
    marker = "      - run: uv venv .package-smoke --python 3.13\n"
    if marker not in content:
        raise SystemExit("missing package smoke marker in CI workflow")
    source_check = '''      - name: Verify source distribution contents
        run: |
          uv run --frozen --extra dev --python 3.13 python - <<'PY'
          from pathlib import Path
          from tarfile import open as open_tarfile

          source_distributions = tuple(
              Path("dist").glob("rankweave-*.tar.gz")
          )
          if len(source_distributions) != 1:
              raise SystemExit(
                  "package job requires exactly one source distribution"
              )
          source_distribution = source_distributions[0]
          source_root = source_distribution.name.removesuffix(".tar.gz") + "/"
          with open_tarfile(source_distribution, "r:gz") as archive:
              source_members = set(archive.getnames())
          required_source_members = {
              source_root + "pyproject.toml",
              source_root + "README.md",
              source_root + "CHANGELOG.md",
              source_root + "LICENSE",
              source_root + "src/rankweave/__init__.py",
              source_root + "tests/test_version.py",
          }
          missing_source_members = required_source_members - source_members
          if missing_source_members:
              raise SystemExit(
                  "source distribution is missing: "
                  f"{sorted(missing_source_members)!r}"
              )
          PY
'''
    if "Verify source distribution contents" not in content:
        content = content.replace(marker, source_check + marker, 1)
    write(path_text, content)


def update_workflow_contract_test() -> None:
    """Require normal package CI to exercise the release source archive."""
    path_text = "tests/test_publish_workflow.py"
    content = read(path_text)
    test_text = '''

def test_normal_package_ci_builds_and_inspects_source_distribution():
    ci_workflow = _read_repository_file(".github/workflows/ci.yml")

    assert "uv build --wheel --sdist --out-dir dist" in ci_workflow
    assert "Verify source distribution contents" in ci_workflow
    assert "package job requires exactly one source distribution" in ci_workflow
    assert 'source_root + "CHANGELOG.md"' in ci_workflow
    assert 'source_root + "tests/test_version.py"' in ci_workflow
'''
    if "test_normal_package_ci_builds_and_inspects_source_distribution" not in content:
        write(path_text, content.rstrip() + test_text)


def fix_plan_red_expectation() -> None:
    """Align the historical red expectation with the final bounded scope."""
    replace_once(
        "docs/superpowers/plans/2026-08-05-trusted-pypi-release.md",
        "Expected: FAIL because `.github/workflows/publish.yml` does not exist "
        "and current CI/hourly action SHAs do not match the Node.js 24 "
        "allowlist.",
        "Expected: FAIL because `.github/workflows/publish.yml` and "
        "`docs/releasing.md` do not yet exist.",
        "red expectation",
    )


def update_design_ci_evidence() -> None:
    """Record the permanent pull-request source-distribution validation lane."""
    path_text = (
        "docs/superpowers/specs/"
        "2026-08-05-trusted-pypi-release-design.md"
    )
    content = read(path_text)
    marker = (
        "The existing Python 3.10–3.13 matrix remains the runtime "
        "compatibility gate. The release build uses Python 3.13 as the "
        "deterministic packaging interpreter.\n"
    )
    replacement = (
        marker
        + "The ordinary pull-request package job also builds and inspects the "
        "source distribution, so archive completeness is exercised before a "
        "GitHub Release can exist.\n"
    )
    if "ordinary pull-request package job also builds" not in content:
        if marker not in content:
            raise SystemExit("missing design CI evidence marker")
        content = content.replace(marker, replacement, 1)
    write(path_text, content)


def main() -> None:
    """Apply the final release-validation changes."""
    update_ci_source_distribution_gate()
    update_workflow_contract_test()
    fix_plan_red_expectation()
    update_design_ci_evidence()


if __name__ == "__main__":
    main()
