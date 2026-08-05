import os
import subprocess
import sys

import pytest

from rankweave import load_report_schema_text
from rankweave.cli import main


@pytest.mark.parametrize(
    ("report_type", "schema_version"),
    [
        ("pairwise", "v1"),
        ("pairwise", "v2"),
        ("family", "v1"),
        ("family", "v2"),
    ],
)
def test_schema_command_emits_exact_packaged_utf8_text(
    capsys, report_type, schema_version
):
    exit_code = main(
        [
            "schema",
            "--report-type",
            report_type,
            "--schema-version",
            schema_version,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == load_report_schema_text(report_type, schema_version)


def test_schema_console_and_module_entrypoints_are_byte_identical_under_ascii_locale():
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii:strict"
    arguments = [
        "schema",
        "--report-type",
        "family",
        "--schema-version",
        "v2",
    ]

    module = subprocess.run(
        [sys.executable, "-m", "rankweave", *arguments],
        check=False,
        capture_output=True,
        env=environment,
    )
    console = subprocess.run(
        [
            sys.executable,
            "-c",
            "from rankweave.cli import main; raise SystemExit(main())",
            *arguments,
        ],
        check=False,
        capture_output=True,
        env=environment,
    )

    assert module.returncode == 0, module.stderr.decode("utf-8", errors="replace")
    assert console.returncode == 0, console.stderr.decode(
        "utf-8", errors="replace"
    )
    assert module.stderr == b""
    assert console.stderr == b""
    assert module.stdout == console.stdout
    assert module.stdout.decode("utf-8") == load_report_schema_text("family", "v2")


@pytest.mark.parametrize(
    "arguments",
    [
        ["schema"],
        ["schema", "--report-type", "pairwise"],
        ["schema", "--schema-version", "v1"],
        [
            "schema",
            "--report-type",
            "unknown",
            "--schema-version",
            "v1",
        ],
        [
            "schema",
            "--report-type",
            "pairwise",
            "--schema-version",
            "v3",
        ],
    ],
)
def test_schema_command_preserves_stderr_only_exit_two_usage_failures(
    capsys, arguments
):
    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
