import json
from types import SimpleNamespace

import pytest

from rankweave.cli import (
    DEFAULT_MAX_INPUT_BYTES,
    OUTPUT_SCHEMA_VERSION,
    build_parser,
    comparison_to_dict,
    main,
    read_text_bounded,
)
from rankweave.trec_comparison import compare_trec_runs

QRELS_TEXT = """
질의-가 0 relevant-a 1
질의-가 0 irrelevant-a 0
query-b 0 relevant-b 1
query-b 0 irrelevant-b 0
"""

BASELINE_RUN_TEXT = """
질의-가 Q0 irrelevant-a 1 0.9 baseline
질의-가 Q0 relevant-a 2 0.2 baseline
query-b Q0 irrelevant-b 1 0.8 baseline
query-b Q0 relevant-b 2 0.1 baseline
"""

CANDIDATE_RUN_TEXT = """
질의-가 Q0 relevant-a 1 0.9 candidate
질의-가 Q0 irrelevant-a 2 0.2 candidate
query-b Q0 relevant-b 1 0.8 candidate
query-b Q0 irrelevant-b 2 0.1 candidate
"""


def _write_artifacts(tmp_path):
    baseline_path = tmp_path / "baseline.run"
    candidate_path = tmp_path / "candidate.run"
    qrels_path = tmp_path / "qrels.txt"
    baseline_path.write_text(BASELINE_RUN_TEXT, encoding="utf-8")
    candidate_path.write_text(CANDIDATE_RUN_TEXT, encoding="utf-8")
    qrels_path.write_text(QRELS_TEXT, encoding="utf-8")
    return baseline_path, candidate_path, qrels_path


def _successful_arguments(tmp_path):
    baseline_path, candidate_path, qrels_path = _write_artifacts(tmp_path)
    return [
        "compare",
        "--baseline-run",
        str(baseline_path),
        "--candidate-run",
        str(candidate_path),
        "--qrels",
        str(qrels_path),
        "--cutoff",
        "1",
        "--alternative",
        "candidate-greater",
    ]


def test_cli_emits_versioned_compact_unicode_json(tmp_path, capsys):
    exit_code = main(_successful_arguments(tmp_path))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert "\n  " not in captured.out
    assert list(payload) == [
        "schema_version",
        "rankweave_version",
        "baseline_run_id",
        "candidate_run_id",
        "cutoff",
        "metric_name",
        "alternative",
        "query_count",
        "nonzero_difference_count",
        "baseline_mean",
        "candidate_mean",
        "mean_difference",
        "p_value",
        "method",
        "randomizations_evaluated",
        "random_seed",
        "query_differences",
    ]
    assert payload["schema_version"] == OUTPUT_SCHEMA_VERSION
    assert payload["baseline_run_id"] == "baseline"
    assert payload["candidate_run_id"] == "candidate"
    assert payload["cutoff"] == 1
    assert payload["metric_name"] == "ndcg_at_k"
    assert payload["alternative"] == "candidate-greater"
    assert payload["mean_difference"] == 1.0
    assert payload["p_value"] == pytest.approx(0.25)
    assert payload["query_differences"][0]["query_id"] == "질의-가"
    assert "질의-가" in captured.out
    assert "\\uc9c8" not in captured.out


def test_cli_pretty_output_and_explicit_statistics(tmp_path, capsys):
    arguments = _successful_arguments(tmp_path) + [
        "--metric",
        "precision_at_k",
        "--randomizations",
        "123",
        "--seed",
        "-7",
        "--max-input-bytes",
        str(DEFAULT_MAX_INPUT_BYTES),
        "--pretty",
    ]

    exit_code = main(arguments)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{\n  \"schema_version\"")
    assert payload["metric_name"] == "precision_at_k"
    assert payload["randomizations_evaluated"] == 4
    assert payload["random_seed"] is None


def test_comparison_projection_matches_immutable_report():
    report = compare_trec_runs(
        BASELINE_RUN_TEXT,
        CANDIDATE_RUN_TEXT,
        QRELS_TEXT,
        cutoff=1,
        alternative="candidate-greater",
    )

    payload = comparison_to_dict(report)

    assert payload["baseline_run_id"] == report.baseline_run.run_id
    assert payload["candidate_run_id"] == report.candidate_run.run_id
    assert payload["mean_difference"] == report.comparison.significance.mean_difference
    assert payload["query_differences"] == [
        {
            "query_id": difference.query_id,
            "baseline_value": difference.baseline_value,
            "candidate_value": difference.candidate_value,
            "difference": difference.difference,
        }
        for difference in report.comparison.significance.query_differences
    ]


def test_parser_documents_compare_defaults():
    arguments = build_parser().parse_args(
        [
            "compare",
            "--baseline-run",
            "baseline",
            "--candidate-run",
            "candidate",
            "--qrels",
            "qrels",
            "--cutoff",
            "10",
        ]
    )

    assert arguments.metric == "ndcg_at_k"
    assert arguments.alternative == "two-sided"
    assert arguments.randomizations == 10_000
    assert arguments.seed == 0
    assert arguments.max_input_bytes == DEFAULT_MAX_INPUT_BYTES
    assert arguments.pretty is False


@pytest.mark.parametrize(
    ("extra_arguments", "message"),
    [
        (["--cutoff", "0"], "cutoff must be a positive integer"),
        (["--randomizations", "1.5"], "randomizations must be a positive integer"),
        (["--max-input-bytes", "-1"], "max-input-bytes must be a positive integer"),
        (["--seed", "1.5"], "seed must be an integer"),
        (["--metric", "map"], "invalid choice"),
        (["--alternative", "greater"], "invalid choice"),
    ],
)
def test_cli_rejects_invalid_options(tmp_path, capsys, extra_arguments, message):
    arguments = _successful_arguments(tmp_path)
    option_name = extra_arguments[0]
    option_index = arguments.index(option_name) if option_name in arguments else None
    if option_index is not None:
        arguments[option_index : option_index + 2] = extra_arguments
    else:
        arguments.extend(extra_arguments)

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert message in captured.err


def test_cli_rejects_missing_required_arguments(capsys):
    exit_code = main(["compare"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert "required" in captured.err


@pytest.mark.parametrize(
    ("path_kind", "message"),
    [
        ("missing", "No such file"),
        ("directory", "Is a directory"),
    ],
)
def test_cli_reports_file_io_errors(tmp_path, capsys, path_kind, message):
    arguments = _successful_arguments(tmp_path)
    if path_kind == "missing":
        invalid_path = tmp_path / "missing.run"
    else:
        invalid_path = tmp_path / "run-directory"
        invalid_path.mkdir()
    arguments[2] = str(invalid_path)

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert message in captured.err


def test_cli_rejects_invalid_utf8(tmp_path, capsys):
    arguments = _successful_arguments(tmp_path)
    invalid_path = tmp_path / "invalid.run"
    invalid_path.write_bytes(b"\xff\xfe")
    arguments[2] = str(invalid_path)

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert "valid UTF-8" in captured.err


def test_cli_rejects_oversized_input_before_read(tmp_path, capsys):
    arguments = _successful_arguments(tmp_path) + ["--max-input-bytes", "4"]

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "exceeds max-input-bytes 4" in captured.err


def test_bounded_reader_rechecks_actual_byte_count(monkeypatch, tmp_path):
    path = tmp_path / "growing.run"
    path.write_bytes(b"0123456789")
    original_stat = type(path).stat

    def small_stat(self):
        if self == path:
            return SimpleNamespace(st_size=1)
        return original_stat(self)

    monkeypatch.setattr(type(path), "stat", small_stat)

    with pytest.raises(ValueError, match="exceeds max-input-bytes 4"):
        read_text_bounded(path, 4)


def test_cli_preserves_precise_trec_validation_error(tmp_path, capsys):
    arguments = _successful_arguments(tmp_path)
    malformed_path = tmp_path / "malformed.run"
    malformed_path.write_text("query Q0 document 0 1.0 run\n", encoding="utf-8")
    arguments[2] = str(malformed_path)

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert "rank must be a positive integer" in captured.err
