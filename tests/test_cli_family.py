import json
from types import SimpleNamespace

import pytest

from rankweave.cli import (
    DEFAULT_MAX_INPUT_BYTES,
    FAMILY_OUTPUT_SCHEMA_VERSION,
    build_parser,
    family_comparison_to_dict,
    main,
    parse_candidate_specifications,
)
from rankweave.trec_family_comparison import compare_trec_run_family

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

CANDIDATE_A_RUN_TEXT = """
질의-가 Q0 relevant-a 1 0.9 candidate-a
질의-가 Q0 irrelevant-a 2 0.2 candidate-a
query-b Q0 relevant-b 1 0.8 candidate-a
query-b Q0 irrelevant-b 2 0.1 candidate-a
"""

CANDIDATE_B_RUN_TEXT = """
질의-가 Q0 relevant-a 1 0.95 candidate-b
질의-가 Q0 irrelevant-a 2 0.10 candidate-b
query-b Q0 relevant-b 1 0.85 candidate-b
query-b Q0 irrelevant-b 2 0.05 candidate-b
"""


def _write_family_artifacts(tmp_path):
    baseline_path = tmp_path / "baseline.run"
    candidate_a_path = tmp_path / "candidate-a.run"
    candidate_b_path = tmp_path / "candidate=b.run"
    qrels_path = tmp_path / "qrels.txt"
    baseline_path.write_text(BASELINE_RUN_TEXT, encoding="utf-8")
    candidate_a_path.write_text(CANDIDATE_A_RUN_TEXT, encoding="utf-8")
    candidate_b_path.write_text(CANDIDATE_B_RUN_TEXT, encoding="utf-8")
    qrels_path.write_text(QRELS_TEXT, encoding="utf-8")
    return baseline_path, candidate_a_path, candidate_b_path, qrels_path


def _successful_family_arguments(tmp_path):
    baseline_path, candidate_a_path, candidate_b_path, qrels_path = (
        _write_family_artifacts(tmp_path)
    )
    return [
        "compare-family",
        "--baseline-run",
        str(baseline_path),
        "--candidate",
        f"모델-a={candidate_a_path}",
        "--candidate",
        f"model-b={candidate_b_path}",
        "--qrels",
        str(qrels_path),
        "--cutoff",
        "1",
        "--alternative",
        "candidate-greater",
    ]


def test_family_cli_emits_ordered_versioned_compact_json(tmp_path, capsys):
    exit_code = main(_successful_family_arguments(tmp_path))

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
        "cutoff",
        "metric_name",
        "alternative",
        "familywise_alpha",
        "candidate_count",
        "candidates",
    ]
    assert payload["schema_version"] == FAMILY_OUTPUT_SCHEMA_VERSION
    assert payload["baseline_run_id"] == "baseline"
    assert payload["cutoff"] == 1
    assert payload["metric_name"] == "ndcg_at_k"
    assert payload["alternative"] == "candidate-greater"
    assert payload["familywise_alpha"] == 0.05
    assert payload["candidate_count"] == 2
    assert [candidate["candidate_id"] for candidate in payload["candidates"]] == [
        "모델-a",
        "model-b",
    ]
    first = payload["candidates"][0]
    assert list(first) == [
        "candidate_id",
        "candidate_run_id",
        "query_count",
        "nonzero_difference_count",
        "baseline_mean",
        "candidate_mean",
        "mean_difference",
        "raw_p_value",
        "holm_adjusted_p_value",
        "rejected_at_familywise_alpha",
        "method",
        "randomizations_evaluated",
        "random_seed",
        "query_differences",
    ]
    assert first["candidate_run_id"] == "candidate-a"
    assert first["mean_difference"] == 1.0
    assert first["raw_p_value"] == pytest.approx(0.25)
    assert first["holm_adjusted_p_value"] == pytest.approx(0.5)
    assert first["rejected_at_familywise_alpha"] is False
    assert first["query_differences"][0]["query_id"] == "질의-가"
    assert "모델-a" in captured.out
    assert "\\ubaa8" not in captured.out


def test_family_cli_pretty_output_and_explicit_statistics(tmp_path, capsys):
    arguments = _successful_family_arguments(tmp_path) + [
        "--metric",
        "precision_at_k",
        "--familywise-alpha",
        "0.5",
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
    assert payload["familywise_alpha"] == 0.5
    assert payload["candidates"][0]["randomizations_evaluated"] == 4
    assert payload["candidates"][0]["random_seed"] is None


def test_family_projection_matches_immutable_report():
    report = compare_trec_run_family(
        BASELINE_RUN_TEXT,
        {
            "first": CANDIDATE_A_RUN_TEXT,
            "second": CANDIDATE_B_RUN_TEXT,
        },
        QRELS_TEXT,
        cutoff=1,
        alternative="candidate-greater",
    )

    payload = family_comparison_to_dict(report)

    assert payload["baseline_run_id"] == report.baseline_run.run_id
    assert payload["candidate_count"] == len(report.candidates)
    assert payload["familywise_alpha"] == report.familywise_alpha
    for projected, candidate in zip(
        payload["candidates"], report.candidates, strict=True
    ):
        significance = candidate.comparison.significance
        assert projected["candidate_id"] == candidate.candidate_id
        assert projected["candidate_run_id"] == candidate.candidate_run.run_id
        assert projected["raw_p_value"] == candidate.raw_p_value
        assert projected["holm_adjusted_p_value"] == candidate.holm_adjusted_p_value
        assert projected["mean_difference"] == significance.mean_difference
        assert projected["query_differences"] == [
            {
                "query_id": difference.query_id,
                "baseline_value": difference.baseline_value,
                "candidate_value": difference.candidate_value,
                "difference": difference.difference,
            }
            for difference in significance.query_differences
        ]


def test_family_parser_documents_defaults():
    arguments = build_parser().parse_args(
        [
            "compare-family",
            "--baseline-run",
            "baseline",
            "--candidate",
            "model=candidate",
            "--qrels",
            "qrels",
            "--cutoff",
            "10",
        ]
    )

    assert arguments.candidate_specs == ["model=candidate"]
    assert arguments.metric == "ndcg_at_k"
    assert arguments.alternative == "two-sided"
    assert arguments.familywise_alpha == 0.05
    assert arguments.randomizations == 10_000
    assert arguments.seed == 0
    assert arguments.max_input_bytes == DEFAULT_MAX_INPUT_BYTES
    assert arguments.pretty is False


def test_candidate_specifications_preserve_order_and_equals_in_paths():
    candidates = parse_candidate_specifications(
        ["first=/tmp/one.run", "second=/tmp/candidate=two.run"]
    )

    assert list(candidates.items()) == [
        ("first", "/tmp/one.run"),
        ("second", "/tmp/candidate=two.run"),
    ]


@pytest.mark.parametrize(
    ("specifications", "message"),
    [
        ([], "at least one --candidate"),
        (["missing-separator"], "ID=PATH"),
        (["=candidate.run"], "identifier must not be empty"),
        (["model="], "path must not be empty"),
        ([" model=candidate.run"], "leading or trailing whitespace"),
        (["model =candidate.run"], "leading or trailing whitespace"),
        (["model=candidate.run", "model=other.run"], "duplicate candidate"),
        (["bad\nname=candidate.run"], "printable characters"),
    ],
)
def test_candidate_specifications_reject_invalid_values(specifications, message):
    with pytest.raises(ValueError, match=message):
        parse_candidate_specifications(specifications)


@pytest.mark.parametrize(
    ("extra_arguments", "message"),
    [
        (["--familywise-alpha", "0"], "familywise-alpha must be in"),
        (["--familywise-alpha", "1.1"], "familywise-alpha must be in"),
        (["--familywise-alpha", "nan"], "familywise-alpha must be finite"),
        (["--familywise-alpha", "inf"], "familywise-alpha must be finite"),
        (["--familywise-alpha", "text"], "familywise-alpha must be a number"),
        (["--cutoff", "0"], "cutoff must be a positive integer"),
        (["--randomizations", "1.5"], "randomizations must be a positive integer"),
        (["--max-input-bytes", "-1"], "max-input-bytes must be a positive integer"),
        (["--seed", "1.5"], "seed must be an integer"),
    ],
)
def test_family_cli_rejects_invalid_options(
    tmp_path, capsys, extra_arguments, message
):
    arguments = _successful_family_arguments(tmp_path)
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


def test_family_cli_rejects_duplicate_candidate_identifiers(tmp_path, capsys):
    arguments = _successful_family_arguments(tmp_path)
    arguments[6] = arguments[4]

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "duplicate candidate identifier '모델-a'" in captured.err


def test_family_cli_reports_candidate_specific_trec_error(tmp_path, capsys):
    arguments = _successful_family_arguments(tmp_path)
    malformed_path = tmp_path / "malformed.run"
    malformed_path.write_text("query Q0 document 0 1.0 run\n", encoding="utf-8")
    arguments[6] = f"model-b={malformed_path}"

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("rankweave: error: ")
    assert "candidate 'model-b':" in captured.err
    assert "rank must be a positive integer" in captured.err


def test_family_cli_applies_byte_limit_to_each_candidate(tmp_path, capsys):
    arguments = _successful_family_arguments(tmp_path) + ["--max-input-bytes", "4"]

    exit_code = main(arguments)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "exceeds max-input-bytes 4" in captured.err


def test_family_projection_rejects_non_string_candidate_identifier():
    report = compare_trec_run_family(
        BASELINE_RUN_TEXT,
        {1: CANDIDATE_A_RUN_TEXT},
        QRELS_TEXT,
        cutoff=1,
    )

    with pytest.raises(ValueError, match="candidate identifiers must be strings"):
        family_comparison_to_dict(report)


def test_family_projection_rejects_wrong_report_type():
    with pytest.raises(ValueError, match="TrecRunFamilyComparisonReport"):
        family_comparison_to_dict(SimpleNamespace())
