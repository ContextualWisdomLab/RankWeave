import copy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from rankweave import (
    ReportSchemaDescriptor,
    available_report_schemas,
    load_report_schema,
    load_report_schema_text,
)
from rankweave.cli import main

QRELS = "q 0 relevant 1\nq 0 irrelevant 0\n"
BASELINE = (
    "q Q0 irrelevant 1 0.9 baseline\n"
    "q Q0 relevant 2 0.2 baseline\n"
)
CANDIDATE = (
    "q Q0 relevant 1 0.9 candidate\n"
    "q Q0 irrelevant 2 0.2 candidate\n"
)
SECOND_CANDIDATE = (
    "q Q0 relevant 1 0.95 candidate-b\n"
    "q Q0 irrelevant 2 0.10 candidate-b\n"
)

EXPECTED_DESCRIPTORS = (
    ReportSchemaDescriptor(
        report_type="pairwise",
        schema_version="v1",
        transport_schema_id="rankweave.trec-comparison.v1",
        resource_name="trec-comparison-v1.schema.json",
    ),
    ReportSchemaDescriptor(
        report_type="pairwise",
        schema_version="v2",
        transport_schema_id="rankweave.trec-comparison.v2",
        resource_name="trec-comparison-v2.schema.json",
    ),
    ReportSchemaDescriptor(
        report_type="family",
        schema_version="v1",
        transport_schema_id="rankweave.trec-family-comparison.v1",
        resource_name="trec-family-comparison-v1.schema.json",
    ),
    ReportSchemaDescriptor(
        report_type="family",
        schema_version="v2",
        transport_schema_id="rankweave.trec-family-comparison.v2",
        resource_name="trec-family-comparison-v2.schema.json",
    ),
)


def _write_artifacts(tmp_path):
    baseline_path = tmp_path / "baseline.run"
    candidate_path = tmp_path / "candidate.run"
    second_candidate_path = tmp_path / "candidate-b.run"
    qrels_path = tmp_path / "qrels.txt"
    baseline_path.write_text(BASELINE, encoding="utf-8")
    candidate_path.write_text(CANDIDATE, encoding="utf-8")
    second_candidate_path.write_text(SECOND_CANDIDATE, encoding="utf-8")
    qrels_path.write_text(QRELS, encoding="utf-8")
    return baseline_path, candidate_path, second_candidate_path, qrels_path


def _generate_report(tmp_path, capsys, report_type, schema_version):
    baseline_path, candidate_path, second_candidate_path, qrels_path = (
        _write_artifacts(tmp_path)
    )
    if report_type == "pairwise":
        arguments = [
            "compare",
            "--baseline-run",
            str(baseline_path),
            "--candidate-run",
            str(candidate_path),
            "--qrels",
            str(qrels_path),
            "--cutoff",
            "1",
        ]
    else:
        arguments = [
            "compare-family",
            "--baseline-run",
            str(baseline_path),
            "--candidate",
            f"first={candidate_path}",
            "--candidate",
            f"second={second_candidate_path}",
            "--qrels",
            str(qrels_path),
            "--cutoff",
            "1",
        ]
    if schema_version == "v2":
        arguments.append("--include-artifact-digests")
    assert main(arguments) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_schema_descriptors_are_frozen_complete_and_stably_ordered():
    descriptors = available_report_schemas()

    assert descriptors == EXPECTED_DESCRIPTORS
    assert available_report_schemas() is descriptors
    with pytest.raises(AttributeError):
        descriptors[0].report_type = "changed"


@pytest.mark.parametrize(
    ("report_type", "schema_version"),
    [
        ("pairwise", "v1"),
        ("pairwise", "v2"),
        ("family", "v1"),
        ("family", "v2"),
    ],
)
def test_packaged_schemas_are_draft_2020_12_and_meta_schema_valid(
    report_type, schema_version
):
    text = load_report_schema_text(report_type, schema_version)
    schema = load_report_schema(report_type, schema_version)

    assert text.endswith("\n")
    assert json.loads(text) == schema
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["schema_version"] if False else True
    Draft202012Validator.check_schema(schema)


def test_parsed_schema_loads_are_fresh_and_cannot_mutate_future_results():
    first = load_report_schema("pairwise", "v2")
    second = load_report_schema("pairwise", "v2")

    assert first == second
    assert first is not second
    first["title"] = "mutated"
    assert load_report_schema("pairwise", "v2")["title"] != "mutated"


@pytest.mark.parametrize(
    ("report_type", "schema_version", "message"),
    [
        ("unknown", "v1", "report_type must be one of"),
        ("pairwise", "v3", "schema_version must be one of"),
        (1, "v1", "report_type must be one of"),
        ("pairwise", 1, "schema_version must be one of"),
    ],
)
def test_schema_loaders_fail_closed_for_unknown_selectors(
    report_type, schema_version, message
):
    with pytest.raises(ValueError, match=message):
        load_report_schema_text(report_type, schema_version)
    with pytest.raises(ValueError, match=message):
        load_report_schema(report_type, schema_version)


@pytest.mark.parametrize(
    ("report_type", "schema_version"),
    [
        ("pairwise", "v1"),
        ("pairwise", "v2"),
        ("family", "v1"),
        ("family", "v2"),
    ],
)
def test_real_cli_reports_validate_against_their_packaged_schemas(
    tmp_path, capsys, report_type, schema_version
):
    report = _generate_report(tmp_path, capsys, report_type, schema_version)
    validator = Draft202012Validator(
        load_report_schema(report_type, schema_version)
    )

    validator.validate(report)


@pytest.mark.parametrize(
    ("mutation", "schema_path"),
    [
        (lambda value: value.pop("cutoff"), ("pairwise", "v1")),
        (lambda value: value.update(extra="forbidden"), ("pairwise", "v1")),
        (lambda value: value.update(metric_name="map"), ("pairwise", "v1")),
        (
            lambda value: value["artifacts"]["candidate_run"].update(
                sha256="not-a-sha256"
            ),
            ("pairwise", "v2"),
        ),
        (
            lambda value: value["artifacts"]["qrels"].update(byte_count=-1),
            ("family", "v2"),
        ),
    ],
)
def test_schema_rejects_representative_contract_violations(
    tmp_path, capsys, mutation, schema_path
):
    report_type, schema_version = schema_path
    report = _generate_report(tmp_path, capsys, report_type, schema_version)
    invalid_report = copy.deepcopy(report)
    mutation(invalid_report)
    validator = Draft202012Validator(
        load_report_schema(report_type, schema_version)
    )

    with pytest.raises(ValidationError):
        validator.validate(invalid_report)
