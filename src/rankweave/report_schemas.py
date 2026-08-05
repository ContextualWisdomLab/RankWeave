"""Discover and load packaged JSON Schemas for RankWeave reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

_REPORT_TYPES = ("pairwise", "family")
_SCHEMA_VERSIONS = ("v1", "v2")


@dataclass(frozen=True)
class ReportSchemaDescriptor:
    """Describe one packaged RankWeave report schema resource."""

    report_type: str
    schema_version: str
    transport_schema_id: str
    resource_name: str


_REPORT_SCHEMAS = (
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


def available_report_schemas() -> tuple[ReportSchemaDescriptor, ...]:
    """Return all packaged report schemas in stable discovery order."""
    return _REPORT_SCHEMAS


def _require_selector(value: object, *, label: str, supported: tuple[str, ...]) -> str:
    """Return a supported schema selector or raise a stable validation error."""
    if not isinstance(value, str) or value not in supported:
        raise ValueError(f"{label} must be one of {supported!r}")
    return value


def _schema_descriptor(
    report_type: object,
    schema_version: object,
) -> ReportSchemaDescriptor:
    """Return the descriptor selected by validated public identifiers."""
    validated_type = _require_selector(
        report_type,
        label="report_type",
        supported=_REPORT_TYPES,
    )
    validated_version = _require_selector(
        schema_version,
        label="schema_version",
        supported=_SCHEMA_VERSIONS,
    )
    for descriptor in _REPORT_SCHEMAS:
        if (
            descriptor.report_type == validated_type
            and descriptor.schema_version == validated_version
        ):
            return descriptor
    raise RuntimeError("validated report schema descriptor is missing")


def load_report_schema_text(report_type: object, schema_version: object) -> str:
    """Load one packaged Draft 2020-12 schema as canonical UTF-8 text."""
    descriptor = _schema_descriptor(report_type, schema_version)
    resource = files("rankweave.schemas").joinpath(descriptor.resource_name)
    return resource.read_text(encoding="utf-8").rstrip("\n") + "\n"


def load_report_schema(
    report_type: object,
    schema_version: object,
) -> dict[str, Any]:
    """Load one packaged schema as a fresh mutable JSON object."""
    parsed = json.loads(load_report_schema_text(report_type, schema_version))
    if not isinstance(parsed, dict):
        raise RuntimeError("packaged report schema root must be a JSON object")
    return parsed
