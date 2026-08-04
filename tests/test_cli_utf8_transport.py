import json
import os
import subprocess
import sys


def test_family_cli_writes_utf8_bytes_when_text_stdout_is_ascii(tmp_path):
    baseline_path = tmp_path / "baseline.run"
    candidate_path = tmp_path / "candidate.run"
    qrels_path = tmp_path / "qrels.txt"
    baseline_path.write_text(
        "q Q0 irrelevant 1 0.9 baseline\n"
        "q Q0 relevant 2 0.2 baseline\n",
        encoding="utf-8",
    )
    candidate_path.write_text(
        "q Q0 relevant 1 0.9 candidate\n"
        "q Q0 irrelevant 2 0.2 candidate\n",
        encoding="utf-8",
    )
    qrels_path.write_text(
        "q 0 relevant 1\nq 0 irrelevant 0\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii:strict"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rankweave",
            "compare-family",
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"모델={candidate_path}",
            "--qrels",
            str(qrels_path),
            "--cutoff",
            "1",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    payload = json.loads(completed.stdout.decode("utf-8"))
    assert payload["candidates"][0]["candidate_id"] == "모델"
