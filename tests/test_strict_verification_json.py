"""Fail-closed persisted-report JSON parsing contracts."""

import pytest

from rankweave.cli import _load_report_json


def test_strict_report_json_accepts_unique_standard_members():
    """Preserve ordinary RFC 8259 JSON values."""
    assert _load_report_json('{"schema_version":"example","count":1}') == {
        "schema_version": "example",
        "count": 1,
    }


def test_strict_report_json_rejects_duplicate_object_names():
    """Reject implementation-dependent duplicate-member interpretation."""
    with pytest.raises(
        ValueError,
        match="duplicate object name 'schema_version'",
    ):
        _load_report_json(
            '{"schema_version":"first","schema_version":"second"}'
        )


@pytest.mark.parametrize("raw_number", ["NaN", "Infinity", "-Infinity"])
def test_strict_report_json_rejects_nonstandard_numbers(raw_number):
    """Reject numeric spellings outside the RFC 8259 grammar."""
    with pytest.raises(ValueError, match="non-standard number"):
        _load_report_json(f'{{"value":{raw_number}}}')
