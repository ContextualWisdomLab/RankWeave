"""Apply the final PR 20 unprivileged-execution hardening."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()
WORKFLOW_PATH = ROOT / ".github/workflows/hourly-commercialization-loop.yml"
TEST_PATH = ROOT / "tests/test_hourly_commercialization_workflow.py"


def block(*lines: str) -> str:
    """Join exact text lines with a final newline."""
    return "\n".join(lines) + "\n"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace exactly one reviewed fragment and fail closed on drift."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one fragment, found {count}")
    return text.replace(old, new, 1)


def replace_pattern_once(
    text: str,
    pattern: str,
    replacement: str,
    *,
    label: str,
) -> str:
    """Replace one regular-expression span and fail closed on drift."""
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label}: expected one span, found {count}")
    return updated


def replace_step(
    workflow: str,
    step_name: str,
    next_step_name: str,
    replacement: str,
) -> str:
    """Replace one complete named workflow step before its known successor."""
    start_marker = f"      - name: {step_name}\n"
    end_marker = f"\n      - name: {next_step_name}\n"
    if workflow.count(start_marker) != 1:
        raise RuntimeError(f"step {step_name!r} is missing or duplicated")
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start)
    return workflow[:start] + replacement.rstrip("\n") + workflow[end:]


def patch_workflow() -> None:
    """Run untrusted tests without credentials, capabilities, or write access."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    trusted_tooling_step = block(
        "      - name: Prepare trusted validation tooling",
        "        if: steps.gate.outputs.eligible == 'true'",
        "        run: |",
        "          set -euo pipefail",
        '          venv="/tmp/rankweave-automation-venv-${GITHUB_RUN_ID}"',
        '          sudo rm -rf "$venv"',
        '          python -m venv "$venv"',
        '          "$venv/bin/python" -m pip install --upgrade pip',
        '          "$venv/bin/python" -m pip install -e ".[dev]" hatchling',
        '          sudo chown -R root:root "$venv"',
        '          sudo chmod -R a-w "$venv"',
        '          sandbox_uid="$(id -u nobody)"',
        '          sandbox_gid="$(id -g nobody)"',
        "          command -v setpriv >/dev/null",
        '          echo "AUTOMATION_VENV=$venv" >>"$GITHUB_ENV"',
        '          echo "AUTOMATION_BASE_SHA=$(git rev-parse HEAD)" >>"$GITHUB_ENV"',
        '          echo "SANDBOX_UID=$sandbox_uid" >>"$GITHUB_ENV"',
        '          echo "SANDBOX_GID=$sandbox_gid" >>"$GITHUB_ENV"',
        "          {",
        '            echo "/opencode.json"',
        '            echo "/.agent-red-output.txt"',
        '            echo "/PR_MESSAGE.md"',
        '          } >>"$GITHUB_WORKSPACE/.git/info/exclude"',
    )
    workflow = replace_step(
        workflow,
        "Prepare trusted validation tooling",
        "Verify the trusted base and network-isolation primitive",
        trusted_tooling_step,
    )

    probe_step = block(
        "      - name: Verify the trusted base and network-isolation primitive",
        "        if: steps.gate.outputs.eligible == 'true'",
        "        run: |",
        "          set -euo pipefail",
        '          "$AUTOMATION_VENV/bin/python" -m ruff check .',
        '          "$AUTOMATION_VENV/bin/python" -m coverage run -m pytest -q',
        '          "$AUTOMATION_VENV/bin/python" -m coverage report',
        "          rm -f .coverage",
        "          sandbox_probe=(",
        "            sudo unshare --net --pid --fork --mount-proc",
        "            setpriv",
        '            --reuid="$SANDBOX_UID"',
        '            --regid="$SANDBOX_GID"',
        "            --clear-groups",
        "            --no-new-privs",
        "            --bounding-set=-all",
        "            --inh-caps=-all",
        "            --ambient-caps=-all",
        "          )",
        '          "${sandbox_probe[@]}" true',
    )
    workflow = replace_step(
        workflow,
        "Verify the trusted base and network-isolation primitive",
        "Install the pinned OpenCode CLI",
        probe_step,
    )

    workflow = replace_once(
        workflow,
        block(
            '              if b"\\0" in data:',
            '                  raise SystemExit(f"red phase file contains a NUL byte: {path_text}")',
            "              total_bytes += info.st_size",
        ),
        block(
            '              if b"\\0" in data:',
            '                  raise SystemExit(f"red phase file contains a NUL byte: {path_text}")',
            "              try:",
            '                  data.decode("utf-8", errors="strict")',
            "              except UnicodeDecodeError as exc:",
            "                  raise SystemExit(",
            '                      f"red phase file is not strict UTF-8: {path_text}"',
            "                  ) from exc",
            "              total_bytes += info.st_size",
        ),
        label="red strict UTF-8 boundary",
    )

    red_execution = block(
        '          red_home="/tmp/rankweave-red-home-${GITHUB_RUN_ID}"',
        '          red_output="${RUNNER_TEMP}/red-test-output.txt"',
        '          sudo rm -rf "$red_home"',
        '          sudo mkdir -p "$red_home"',
        '          sudo chown "$SANDBOX_UID:$SANDBOX_GID" "$red_home"',
        "          red_sandbox=(",
        "            sudo unshare --net --pid --fork --mount-proc",
        "            setpriv",
        '            --reuid="$SANDBOX_UID"',
        '            --regid="$SANDBOX_GID"',
        "            --clear-groups",
        "            --no-new-privs",
        "            --bounding-set=-all",
        "            --inh-caps=-all",
        "            --ambient-caps=-all",
        "          )",
        "          red_environment=(",
        "            env",
        "            -i",
        '            "PATH=${AUTOMATION_VENV}/bin:/usr/bin:/bin"',
        '            "HOME=$red_home"',
        '            "WORKSPACE=$GITHUB_WORKSPACE"',
        '            "PYTHONPATH=$GITHUB_WORKSPACE/src"',
        "            PYTHONDONTWRITEBYTECODE=1",
        "            bash",
        "            --noprofile",
        "            --norc",
        "            -c",
        "            'cd \"$WORKSPACE\" && python -m pytest -q -p no:cacheprovider'",
        "          )",
        "          set +e",
        '          "${red_sandbox[@]}" "${red_environment[@]}" >"$red_output" 2>&1',
        "          red_status=$?",
    )
    workflow = replace_pattern_once(
        workflow,
        r"          set \+e\n.*?          red_status=\$\?\n",
        red_execution,
        label="red unprivileged sandbox",
    )

    workflow = replace_once(
        workflow,
        block(
            '              if b"\\0" in data:',
            '                  raise SystemExit(f"NUL byte found in {path_text}")',
            "              total_bytes += info.st_size",
        ),
        block(
            '              if b"\\0" in data:',
            '                  raise SystemExit(f"NUL byte found in {path_text}")',
            "              try:",
            '                  data.decode("utf-8", errors="strict")',
            "              except UnicodeDecodeError as exc:",
            "                  raise SystemExit(",
            '                      f"changed file is not strict UTF-8: {path_text}"',
            "                  ) from exc",
            "              total_bytes += info.st_size",
        ),
        label="proposal strict UTF-8 boundary",
    )

    workflow = replace_once(
        workflow,
        block(
            "          rm -f opencode.json .agent-red-output.txt",
            "          git clean -fdX",
        ),
        block(
            '          pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"',
            "          if [ -f PR_MESSAGE.md ]; then",
            '            cp PR_MESSAGE.md "$pr_message_backup"',
            "          fi",
            "          rm -f opencode.json .agent-red-output.txt",
            "          git clean -fdX",
            '          if [ -f "$pr_message_backup" ]; then',
            '            cp "$pr_message_backup" PR_MESSAGE.md',
            "          fi",
        ),
        label="ignored-file cleanup",
    )

    validation_step = block(
        "      - name: Validate untrusted changes without network or inherited environment",
        "        if: steps.gate.outputs.eligible == 'true'",
        "        run: |",
        "          set -euo pipefail",
        '          validation_dist="/tmp/rankweave-validation-dist-${GITHUB_RUN_ID}"',
        '          validation_smoke="/tmp/rankweave-validation-smoke-${GITHUB_RUN_ID}"',
        '          validation_home="/tmp/rankweave-validation-home-${GITHUB_RUN_ID}"',
        '          validation_coverage="/tmp/rankweave-validation-${GITHUB_RUN_ID}.coverage"',
        '          ruff_cache="/tmp/rankweave-ruff-cache-${GITHUB_RUN_ID}"',
        '          validation_script="/tmp/rankweave-validate-${GITHUB_RUN_ID}.sh"',
        "          validation_paths=(",
        '            "$validation_dist"',
        '            "$validation_smoke"',
        '            "$validation_home"',
        '            "$validation_coverage"',
        '            "$ruff_cache"',
        '            "$validation_script"',
        "          )",
        '          sudo rm -rf "${validation_paths[@]}"',
        '          sudo mkdir -p "$validation_dist" "$validation_home" "$ruff_cache"',
        '          sudo chown -R "$SANDBOX_UID:$SANDBOX_GID"',
        '            "$validation_dist" "$validation_home" "$ruff_cache"',
        '          cat >"$validation_script" <<\'VALIDATE\'',
        "          set -euo pipefail",
        '          cd "$WORKSPACE"',
        "          python -m ruff check .",
        "          python -m coverage run -m pytest -q -p no:cacheprovider",
        "          python -m coverage report",
        '          python -m pip wheel . --no-deps --no-build-isolation --wheel-dir "$DIST"',
        '          python -m venv "$SMOKE"',
        '          "$SMOKE/bin/python" -m pip install --no-index --find-links "$DIST" rankweave',
        '          "$SMOKE/bin/python" -m pip check',
        '          cd "$HOME"',
        '          "$SMOKE/bin/python" -c',
        "            'from importlib.metadata import version; import rankweave; assert version(\"rankweave\") == rankweave.__version__'",
        "          VALIDATE",
        '          sudo chown root:root "$validation_script"',
        '          sudo chmod 0555 "$validation_script"',
        "          validation_sandbox=(",
        "            sudo unshare --net --pid --fork --mount-proc",
        "            setpriv",
        '            --reuid="$SANDBOX_UID"',
        '            --regid="$SANDBOX_GID"',
        "            --clear-groups",
        "            --no-new-privs",
        "            --bounding-set=-all",
        "            --inh-caps=-all",
        "            --ambient-caps=-all",
        "          )",
        "          validation_environment=(",
        "            env",
        "            -i",
        '            "PATH=${AUTOMATION_VENV}/bin:/usr/bin:/bin"',
        '            "HOME=$validation_home"',
        '            "WORKSPACE=$GITHUB_WORKSPACE"',
        '            "PYTHONPATH=$GITHUB_WORKSPACE/src"',
        '            "DIST=$validation_dist"',
        '            "SMOKE=$validation_smoke"',
        '            "COVERAGE_FILE=$validation_coverage"',
        '            "RUFF_CACHE_DIR=$ruff_cache"',
        "            PYTHONDONTWRITEBYTECODE=1",
        "            PIP_DISABLE_PIP_VERSION_CHECK=1",
        "            PIP_NO_INDEX=1",
        "            bash",
        "            --noprofile",
        "            --norc",
        '            "$validation_script"',
        "          )",
        '          "${validation_sandbox[@]}" "${validation_environment[@]}"',
    )
    workflow = replace_step(
        workflow,
        "Validate untrusted changes without network or inherited environment",
        "Verify validation did not mutate the proposal",
        validation_step,
    )

    workflow = replace_once(
        workflow,
        block(
            "          if [ -f PR_MESSAGE.md ]; then",
            '            "$AUTOMATION_VENV/bin/python" - <<\'PY\'',
        ),
        block(
            "          if [ -f PR_MESSAGE.md ]; then",
            "            /usr/bin/python3 -I -S - <<'PY'",
        ),
        label="trusted PR metadata parser",
    )
    WORKFLOW_PATH.write_text(workflow, encoding="utf-8")


def update_contract_tests() -> None:
    """Pin the unprivileged validation boundary in workflow regression tests."""
    tests = TEST_PATH.read_text(encoding="utf-8").rstrip()
    if "def test_untrusted_execution_drops_privileges" in tests:
        raise RuntimeError("unprivileged execution contract already exists")
    tests += '''


def test_untrusted_execution_drops_privileges():
    workflow = _workflow_text()

    assert 'venv="/tmp/rankweave-automation-venv-${GITHUB_RUN_ID}"' in workflow
    assert 'sudo chown -R root:root "$venv"' in workflow
    assert 'sudo chmod -R a-w "$venv"' in workflow
    assert workflow.count("            setpriv\n") == 3
    assert workflow.count('--reuid="$SANDBOX_UID"') == 3
    assert workflow.count('--regid="$SANDBOX_GID"') == 3
    assert workflow.count("--no-new-privs") == 3
    assert workflow.count("--bounding-set=-all") == 3
    assert workflow.count('PYTHONPATH="$GITHUB_WORKSPACE/src"') == 2
    assert 'pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"' in workflow
    assert "/usr/bin/python3 -I -S - <<'PY'" in workflow
    assert "strict UTF-8" in workflow
'''
    TEST_PATH.write_text(tests + "\n", encoding="utf-8")


def update_docs() -> None:
    """Document the credential-free unprivileged execution boundary."""
    changelog_path = ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
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
    changelog_path.write_text(changelog, encoding="utf-8")


def remove_bootstrap_files() -> None:
    """Remove every one-shot repair file before final verification."""
    for path in (
        ROOT / ".github/workflows/patch-pr20-sandbox-pr.yml",
        ROOT / ".github/workflows/patch-pr20-sandbox.yml",
        ROOT / ".github/scripts/apply_pr20_sandbox_patch.py",
        ROOT / ".github/scripts/materialize_workspace.py",
    ):
        path.unlink(missing_ok=True)


def main() -> int:
    """Apply, test-contract, document, and clean the final hardening."""
    patch_workflow()
    update_contract_tests()
    update_docs()
    remove_bootstrap_files()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
