"""Adjust one parametrized test so validation occurs inside the test body."""

from pathlib import Path

path = Path("tests/test_policy_artifacts.py")
content = path.read_text(encoding="utf-8")
invalid_case = """        (
            {
                "channel_weights": (
                    FusionPolicyChannelWeight(" lexical", 0.5),
                    FusionPolicyChannelWeight("dense", 0.5),
                )
            },
            "channel_name",
        ),
"""
if content.count(invalid_case) != 1:
    raise SystemExit("expected one eager invalid channel-weight case")
path.write_text(content.replace(invalid_case, "", 1), encoding="utf-8")
