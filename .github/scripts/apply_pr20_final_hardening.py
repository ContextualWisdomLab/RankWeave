"""Apply and verify PR 20's final unprivileged-execution hardening."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
WORKFLOW_PATH = ROOT / ".github/workflows/hourly-commercialization-loop.yml"
TEST_PATH = ROOT / "tests/test_hourly_commercialization_workflow.py"
TEMP_WORKFLOW_PATH = ROOT / ".github/workflows/apply-pr20-final-hardening.yml"
SELF_PATH = ROOT / ".github/scripts/apply_pr20_final_hardening.py"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace one reviewed fragment and fail closed when the branch drifted."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one fragment, found {count}")
    return text.replace(old, new, 1)


def patch_workflow() -> None:
    """Run model-authored tests without credentials, capabilities, or write access."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = replace_once(
        workflow,
        '''          venv="${RUNNER_TEMP}/rankweave-automation-venv"
          python -m venv "$venv"
          "$venv/bin/python" -m pip install --upgrade pip
          "$venv/bin/python" -m pip install -e ".[dev]" hatchling
          echo "AUTOMATION_VENV=$venv" >>"$GITHUB_ENV"
          echo "AUTOMATION_BASE_SHA=$(git rev-parse HEAD)" >>"$GITHUB_ENV"
''',
        '''          venv="/tmp/rankweave-automation-venv-${GITHUB_RUN_ID}"
          sudo rm -rf "$venv"
          python -m venv "$venv"
          "$venv/bin/python" -m pip install --upgrade pip
          "$venv/bin/python" -m pip install -e ".[dev]" hatchling
          sudo chown -R root:root "$venv"
          sudo chmod -R a-w "$venv"
          sandbox_uid="$(id -u nobody)"
          sandbox_gid="$(id -g nobody)"
          command -v setpriv >/dev/null
          echo "AUTOMATION_VENV=$venv" >>"$GITHUB_ENV"
          echo "AUTOMATION_BASE_SHA=$(git rev-parse HEAD)" >>"$GITHUB_ENV"
          echo "SANDBOX_UID=$sandbox_uid" >>"$GITHUB_ENV"
          echo "SANDBOX_GID=$sandbox_gid" >>"$GITHUB_ENV"
''',
        label="trusted tooling setup",
    )
    workflow = replace_once(
        workflow,
        '''          sudo unshare --net --pid --fork --mount-proc true
''',
        '''          sudo unshare --net --pid --fork --mount-proc \
            setpriv \
              --reuid="$SANDBOX_UID" \
              --regid="$SANDBOX_GID" \
              --clear-groups \
              --no-new-privs \
              --bounding-set=-all \
              --inh-caps=-all \
              --ambient-caps=-all \
              true
''',
        label="namespace privilege-drop probe",
    )
    workflow = replace_once(
        workflow,
        '''              if b"\\0" in data:
                  raise SystemExit(f"red phase file contains a NUL byte: {path_text}")
              total_bytes += info.st_size
''',
        '''              if b"\\0" in data:
                  raise SystemExit(f"red phase file contains a NUL byte: {path_text}")
              try:
                  data.decode("utf-8", errors="strict")
              except UnicodeDecodeError as exc:
                  raise SystemExit(
                      f"red phase file is not strict UTF-8: {path_text}"
                  ) from exc
              total_bytes += info.st_size
''',
        label="red UTF-8 boundary",
    )
    workflow = replace_once(
        workflow,
        '''          set +e
          sudo unshare --net --pid --fork --mount-proc \
            env -i \
              PATH="${AUTOMATION_VENV}/bin:/usr/bin:/bin" \
              HOME="${RUNNER_TEMP}/red-sandbox-home" \
              WORKSPACE="$GITHUB_WORKSPACE" \
              PYTHONDONTWRITEBYTECODE=1 \
              bash --noprofile --norc -c \
              'cd "$WORKSPACE" && python -m pytest -q -p no:cacheprovider' \
            >"${RUNNER_TEMP}/red-test-output.txt" 2>&1
          red_status=$?
''',
        '''          red_home="/tmp/rankweave-red-home-${GITHUB_RUN_ID}"
          sudo rm -rf "$red_home"
          sudo mkdir -p "$red_home"
          sudo chown "$SANDBOX_UID:$SANDBOX_GID" "$red_home"

          set +e
          sudo unshare --net --pid --fork --mount-proc \
            setpriv \
              --reuid="$SANDBOX_UID" \
              --regid="$SANDBOX_GID" \
              --clear-groups \
              --no-new-privs \
              --bounding-set=-all \
              --inh-caps=-all \
              --ambient-caps=-all \
              env -i \
                PATH="${AUTOMATION_VENV}/bin:/usr/bin:/bin" \
                HOME="$red_home" \
                WORKSPACE="$GITHUB_WORKSPACE" \
                PYTHONPATH="$GITHUB_WORKSPACE/src" \
                PYTHONDONTWRITEBYTECODE=1 \
                bash --noprofile --norc -c \
                'cd "$WORKSPACE" && python -m pytest -q -p no:cacheprovider' \
            >"${RUNNER_TEMP}/red-test-output.txt" 2>&1
          red_status=$?
''',
        label="red unprivileged sandbox",
    )
    workflow = replace_once(
        workflow,
        '''              if b"\\0" in data:
                  raise SystemExit(f"NUL byte found in {path_text}")
              total_bytes += info.st_size
''',
        '''              if b"\\0" in data:
                  raise SystemExit(f"NUL byte found in {path_text}")
              try:
                  data.decode("utf-8", errors="strict")
              except UnicodeDecodeError as exc:
                  raise SystemExit(
                      f"changed file is not strict UTF-8: {path_text}"
                  ) from exc
              total_bytes += info.st_size
''',
        label="proposal UTF-8 boundary",
    )
    workflow = replace_once(
        workflow,
        '''          validation_dist="${RUNNER_TEMP}/validation-dist"
          validation_smoke="${RUNNER_TEMP}/validation-smoke"
          rm -rf "$validation_dist" "$validation_smoke"
          mkdir -p "$validation_dist" "${RUNNER_TEMP}/validation-home"

          sudo unshare --net --pid --fork --mount-proc \
            env -i \
              PATH="${AUTOMATION_VENV}/bin:/usr/bin:/bin" \
              HOME="${RUNNER_TEMP}/validation-home" \
              WORKSPACE="$GITHUB_WORKSPACE" \
              DIST="$validation_dist" \
              SMOKE="$validation_smoke" \
              COVERAGE_FILE="${RUNNER_TEMP}/validation.coverage" \
              PYTHONDONTWRITEBYTECODE=1 \
              PIP_DISABLE_PIP_VERSION_CHECK=1 \
              PIP_NO_INDEX=1 \
              bash --noprofile --norc -c '
                set -euo pipefail
                cd "$WORKSPACE"
                python -m ruff check .
                python -m coverage run -m pytest -q -p no:cacheprovider
                python -m coverage report
                python -m pip wheel . --no-deps --no-build-isolation \
                  --wheel-dir "$DIST"
                python -m venv "$SMOKE"
                "$SMOKE/bin/python" -m pip install --no-index \
                  --find-links "$DIST" rankweave
                "$SMOKE/bin/python" -m pip check
                cd "$HOME"
                "$SMOKE/bin/python" -c \
                  "from importlib.metadata import version; import rankweave; assert version(\"rankweave\") == rankweave.__version__"
              '
''',
        '''          validation_dist="/tmp/rankweave-validation-dist-${GITHUB_RUN_ID}"
          validation_smoke="/tmp/rankweave-validation-smoke-${GITHUB_RUN_ID}"
          validation_home="/tmp/rankweave-validation-home-${GITHUB_RUN_ID}"
          validation_coverage="/tmp/rankweave-validation-${GITHUB_RUN_ID}.coverage"
          ruff_cache="/tmp/rankweave-ruff-cache-${GITHUB_RUN_ID}"
          sudo rm -rf \
            "$validation_dist" "$validation_smoke" "$validation_home" \
            "$validation_coverage" "$ruff_cache"
          sudo mkdir -p "$validation_dist" "$validation_home" "$ruff_cache"
          sudo chown -R "$SANDBOX_UID:$SANDBOX_GID" \
            "$validation_dist" "$validation_home" "$ruff_cache"

          sudo unshare --net --pid --fork --mount-proc \
            setpriv \
              --reuid="$SANDBOX_UID" \
              --regid="$SANDBOX_GID" \
              --clear-groups \
              --no-new-privs \
              --bounding-set=-all \
              --inh-caps=-all \
              --ambient-caps=-all \
              env -i \
                PATH="${AUTOMATION_VENV}/bin:/usr/bin:/bin" \
                HOME="$validation_home" \
                WORKSPACE="$GITHUB_WORKSPACE" \
                PYTHONPATH="$GITHUB_WORKSPACE/src" \
                DIST="$validation_dist" \
                SMOKE="$validation_smoke" \
                COVERAGE_FILE="$validation_coverage" \
                RUFF_CACHE_DIR="$ruff_cache" \
                PYTHONDONTWRITEBYTECODE=1 \
                PIP_DISABLE_PIP_VERSION_CHECK=1 \
                PIP_NO_INDEX=1 \
                bash --noprofile --norc -c '
                  set -euo pipefail
                  cd "$WORKSPACE"
                  python -m ruff check .
                  python -m coverage run -m pytest -q -p no:cacheprovider
                  python -m coverage report
                  python -m pip wheel . --no-deps --no-build-isolation \
                    --wheel-dir "$DIST"
                  python -m venv "$SMOKE"
                  "$SMOKE/bin/python" -m pip install --no-index \
                    --find-links "$DIST" rankweave
                  "$SMOKE/bin/python" -m pip check
                  cd "$HOME"
                  "$SMOKE/bin/python" -c \
                    "from importlib.metadata import version; import rankweave; assert version(\"rankweave\") == rankweave.__version__"
                '
''',
        label="final unprivileged sandbox",
    )
    workflow = replace_once(
        workflow,
        '''          rm -f opencode.json .agent-red-output.txt
          git clean -fdX
''',
        '''          pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"
          if [ -f PR_MESSAGE.md ]; then
            cp PR_MESSAGE.md "$pr_message_backup"
          fi
          rm -f opencode.json .agent-red-output.txt
          git clean -fdX
          if [ -f "$pr_message_backup" ]; then
            cp "$pr_message_backup" PR_MESSAGE.md
          fi
''',
        label="ignored-file cleanup",
    )
    workflow = replace_once(
        workflow,
        '''            "$AUTOMATION_VENV/bin/python" - <<'PY'
''',
        '''            /usr/bin/python3 -I -S - <<'PY'
''',
        label="trusted PR metadata parser",
    )
    WORKFLOW_PATH.write_text(workflow, encoding="utf-8")


def update_contract_tests() -> None:
    """Pin the privilege drop and trusted-tooling boundary in tests."""
    tests = TEST_PATH.read_text(encoding="utf-8").rstrip()
    if "def test_untrusted_execution_drops_privileges" in tests:
        raise RuntimeError("unprivileged execution contract already exists")
    tests += '''


def test_untrusted_execution_drops_privileges():
    workflow = _workflow_text()

    assert 'venv="/tmp/rankweave-automation-venv-${GITHUB_RUN_ID}"' in workflow
    assert 'sudo chown -R root:root "$venv"' in workflow
    assert 'sudo chmod -R a-w "$venv"' in workflow
    assert workflow.count('setpriv \\') == 3
    assert workflow.count('--reuid="$SANDBOX_UID"') == 3
    assert workflow.count('--regid="$SANDBOX_GID"') == 3
    assert workflow.count('--no-new-privs') == 3
    assert workflow.count('--bounding-set=-all') == 3
    assert 'PYTHONPATH="$GITHUB_WORKSPACE/src"' in workflow
    assert 'pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"' in workflow
    assert "/usr/bin/python3 -I -S - <<'PY'" in workflow
    assert "strict UTF-8" in workflow
'''
    TEST_PATH.write_text(tests + "\n", encoding="utf-8")


def update_changelog() -> None:
    """Document the credential-free unprivileged execution boundary."""
    path = ROOT / "CHANGELOG.md"
    changelog = path.read_text(encoding="utf-8")
    changelog = replace_once(
        changelog,
        "## [Unreleased]\n",
        '''## [Unreleased]

### Security
- Model-authored red and final tests now run as the unprivileged `nobody` user inside network and PID namespaces with all capability sets removed and `no_new_privs` enabled. Trusted validation tooling is root-owned and read-only before untrusted Python executes.
- Autonomous text boundaries now require strict UTF-8 in addition to regular-file, symlink, NUL, file-count, and byte limits. Ignored PR metadata is preserved across cleanup and parsed with isolated system Python only after validation.
''',
        label="changelog security section",
    )
    path.write_text(changelog, encoding="utf-8")


def run_verification() -> None:
    """Run the repository's complete local quality gate on the patched tree."""
    commands = (
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "coverage", "run", "-m", "pytest", "-q"],
        [sys.executable, "-m", "coverage", "report"],
    )
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)


def remove_bootstrap_files() -> None:
    """Remove one-shot files only after the patched tree passes verification."""
    for path in (TEMP_WORKFLOW_PATH, SELF_PATH):
        path.unlink(missing_ok=True)


def main() -> int:
    """Apply, verify, document, and clean the final hardening."""
    patch_workflow()
    update_contract_tests()
    update_changelog()
    run_verification()
    remove_bootstrap_files()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
