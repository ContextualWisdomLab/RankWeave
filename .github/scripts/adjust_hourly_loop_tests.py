"""Align existing hourly workflow contracts with the read-only repair bridge."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = ROOT / "tests/test_hourly_commercialization_workflow.py"
content = TEST_PATH.read_text(encoding="utf-8")

old_count = 'assert workflow.count("/pulls?state=open&per_page=1") == 3'
if content.count(old_count) != 2:
    raise SystemExit("expected two original global PR-queue count assertions")
content = content.replace(
    old_count,
    'assert workflow.count("/pulls?state=open&per_page=1") == 4',
)

old_permissions = """    for permission in (
        "actions: write",
        "contents: read",
        "issues: write",
        "pull-requests: read",
        "statuses: read",
    ):
        assert permission in repair
    assert "contents: write" not in repair
    assert "id-token: write" not in repair
"""
new_permissions = """    for permission in (
        "contents: read",
        "pull-requests: read",
    ):
        assert permission in repair
    for forbidden_permission in (
        "actions: write",
        "contents: write",
        "id-token: write",
        "issues: write",
        "statuses: read",
    ):
        assert forbidden_permission not in repair
"""
if content.count(old_permissions) != 1:
    raise SystemExit("expected one original review-repair permission contract")
content = content.replace(old_permissions, new_permissions, 1)
TEST_PATH.write_text(content, encoding="utf-8")
