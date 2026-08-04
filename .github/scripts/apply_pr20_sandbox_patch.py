"""Apply the reviewed PR 20 sandbox-hardening repair deterministically."""

from __future__ import annotations

import subprocess
from pathlib import Path

HISTORICAL_SOURCE_COMMIT = "d18eb52fb63488c639cccff6895e8a253af28539"
HISTORICAL_WORKFLOW_PATH = ".github/workflows/patch-pr20-sandbox.yml"
TARGET_WORKFLOW_PATH = ".github/workflows/hourly-commercialization-loop.yml"
TARGET_TEST_PATH = "tests/test_hourly_commercialization_workflow.py"
MATERIALIZER_PATH = ".github/scripts/materialize_workspace.py"


def _historical_patch_source() -> str:
    """Read the reviewed patch program from one immutable repository commit."""
    revision = f"{HISTORICAL_SOURCE_COMMIT}:{HISTORICAL_WORKFLOW_PATH}"
    raw_source = subprocess.check_output(["git", "show", revision])
    return raw_source.decode("utf-8", errors="strict")


def _extract_patch_program(workflow_source: str) -> str:
    """Extract and dedent the Python patch program from the historical workflow."""
    step_start = (
        "      - name: Apply sandbox hardening and remove this workflow\n"
        "        run: |\n"
    )
    step_end = "\n      - name: Verify the repaired branch\n"
    if workflow_source.count(step_start) != 1 or workflow_source.count(step_end) != 1:
        raise RuntimeError("historical one-shot workflow shape drifted")
    run_block = workflow_source.split(step_start, 1)[1].split(step_end, 1)[0]
    opener = "          python - <<'PY'\n"
    closer = "\n          PY"
    if run_block.count(opener) != 1 or not run_block.endswith(closer):
        raise RuntimeError("historical one-shot Python block shape drifted")
    python_source = run_block.split(opener, 1)[1].rsplit(closer, 1)[0]
    dedented_lines = [
        line[10:] if line.startswith("          ") else line
        for line in python_source.splitlines()
    ]
    return "\n".join(dedented_lines) + "\n"


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace exactly one reviewed fragment and fail closed on branch drift."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one fragment, found {count}")
    return text.replace(old, new, 1)


def _preserve_agent_pr_message() -> None:
    """Keep validated PR metadata across ignored-file cleanup."""
    path = Path(TARGET_WORKFLOW_PATH)
    workflow = path.read_text(encoding="utf-8")
    old_clean = (
        "          rm -f opencode.json .agent-red-output.txt\n"
        "          git clean -fdX\n"
    )
    new_clean = (
        '          pr_message_backup="${RUNNER_TEMP}/agent-pr-message.md"\n'
        "          if [ -f PR_MESSAGE.md ]; then\n"
        '            cp PR_MESSAGE.md "$pr_message_backup"\n'
        "          fi\n"
        "          rm -f opencode.json .agent-red-output.txt\n"
        "          git clean -fdX\n"
        '          if [ -f "$pr_message_backup" ]; then\n'
        '            cp "$pr_message_backup" PR_MESSAGE.md\n'
        "          fi\n"
    )
    path.write_text(
        _replace_once(
            workflow,
            old_clean,
            new_clean,
            label="final ignored-file cleanup",
        ),
        encoding="utf-8",
    )


def _sanitize_materialized_file_modes() -> None:
    """Copy only ordinary executable or non-executable file modes."""
    path = Path(MATERIALIZER_PATH)
    helper = path.read_text(encoding="utf-8")
    old_mode = "            os.chmod(target, stat.S_IMODE(info.st_mode))\n"
    new_mode = (
        "            safe_mode = 0o755 if info.st_mode & stat.S_IXUSR else 0o644\n"
        "            os.chmod(target, safe_mode)\n"
    )
    path.write_text(
        _replace_once(
            helper,
            old_mode,
            new_mode,
            label="workspace materializer mode copy",
        ),
        encoding="utf-8",
    )


def _extend_workflow_contract_test() -> None:
    """Pin PR-message preservation and sanitized disposable file modes."""
    path = Path(TARGET_TEST_PATH)
    contracts = path.read_text(encoding="utf-8")
    marker = "    assert 'strict UTF-8' in workflow\n"
    addition = (
        marker
        + "    assert 'pr_message_backup=\"${RUNNER_TEMP}/agent-pr-message.md\"' in workflow\n"  # noqa: E501
        + "    materializer = Path('.github/scripts/materialize_workspace.py').read_text(\n"  # noqa: E501
        + "        encoding='utf-8'\n"
        + "    )\n"
        + "    assert 'safe_mode = 0o755 if info.st_mode & stat.S_IXUSR else 0o644' in materializer\n"  # noqa: E501
    )
    path.write_text(
        _replace_once(
            contracts,
            marker,
            addition,
            label="sandbox contract insertion point",
        ),
        encoding="utf-8",
    )


def _remove_temporary_repair_files() -> None:
    """Remove every temporary workflow and this runner before verification."""
    for path_text in (
        ".github/workflows/patch-pr20-sandbox-pr.yml",
        HISTORICAL_WORKFLOW_PATH,
        ".github/scripts/apply_pr20_sandbox_patch.py",
    ):
        Path(path_text).unlink(missing_ok=True)


def main() -> int:
    """Execute the reviewed repair, harden it, and clean up bootstrap files."""
    source = _extract_patch_program(_historical_patch_source())
    code = compile(
        source, f"{HISTORICAL_SOURCE_COMMIT}:{HISTORICAL_WORKFLOW_PATH}", "exec"
    )
    exec(code, {"__name__": "__main__"})
    _preserve_agent_pr_message()
    _sanitize_materialized_file_modes()
    _extend_workflow_contract_test()
    _remove_temporary_repair_files()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
