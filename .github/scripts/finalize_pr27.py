"""Finalize RankWeave 0.14.0 artifact verification and documentation."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    """Read one repository UTF-8 text file."""
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    """Write one repository UTF-8 text file with a trailing newline."""
    target = REPOSITORY_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip("\n") + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str, label: str) -> None:
    """Replace one exact source fragment and fail closed when it drifts."""
    content = read(path)
    if old not in content:
        raise SystemExit(f"missing {label} anchor in {path}")
    write(path, content.replace(old, new, 1))


def append_once(path: str, marker: str, addition: str) -> None:
    """Append a documented section only when its marker is absent."""
    content = read(path)
    if marker not in content:
        write(path, content.rstrip() + "\n\n" + addition.strip() + "\n")


def install_report_schema_registry() -> None:
    """Publish all pairwise, family, and verification schema descriptors."""
    write(
        "src/rankweave/report_schemas.py",
        '''"""Discover and load packaged JSON Schemas for RankWeave reports."""

from __future__ import annotations

import json
from dataclasses import dataclass

# RankWeave supports Python 3.10+, so the Python 3.7 compatibility rule does not
# apply to this standard-library import.
from importlib.resources import files  # nosemgrep
from typing import Any

_REPORT_TYPES = ("pairwise", "family", "verification")
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
    ReportSchemaDescriptor(
        report_type="verification",
        schema_version="v1",
        transport_schema_id="rankweave.artifact-verification.v1",
        resource_name="artifact-verification-v1.schema.json",
    ),
)
_SUPPORTED_SCHEMA_SELECTORS = frozenset(
    (descriptor.report_type, descriptor.schema_version)
    for descriptor in _REPORT_SCHEMAS
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
    selector = (validated_type, validated_version)
    if selector not in _SUPPORTED_SCHEMA_SELECTORS:
        raise ValueError(
            "schema combination is unsupported: "
            f"report_type={validated_type!r}, "
            f"schema_version={validated_version!r}"
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
    return resource.read_text(encoding="utf-8").rstrip("\\n") + "\\n"


def load_report_schema(
    report_type: object,
    schema_version: object,
) -> dict[str, Any]:
    """Load one packaged schema as a fresh mutable JSON object."""
    parsed = json.loads(load_report_schema_text(report_type, schema_version))
    if not isinstance(parsed, dict):
        raise RuntimeError("packaged report schema root must be a JSON object")
    return parsed
''',
    )
    write(
        "src/rankweave/schemas/artifact-verification-v1.schema.json",
        '''{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://contextualwisdomlab.github.io/rankweave/schemas/artifact-verification-v1.schema.json",
  "title": "RankWeave artifact verification v1",
  "description": "Path-free comparison of explicit local bytes with unsigned SHA-256 and byte-count evidence from one RankWeave v2 report.",
  "$comment": "A matching document proves only exact-byte equality with the supplied unsigned report evidence. It is not producer authentication, signature verification, provenance verification, an attestation, or a SLSA-level claim. Cross-field count, order, candidate-nullability, and match-boolean invariants are enforced by RankWeave producers and consumers.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "rankweave_version",
    "report_schema_version",
    "verified",
    "artifact_count",
    "mismatch_count",
    "artifacts"
  ],
  "properties": {
    "schema_version": {
      "const": "rankweave.artifact-verification.v1"
    },
    "rankweave_version": {
      "type": "string",
      "minLength": 1
    },
    "report_schema_version": {
      "enum": [
        "rankweave.trec-comparison.v2",
        "rankweave.trec-family-comparison.v2"
      ]
    },
    "verified": {
      "type": "boolean"
    },
    "artifact_count": {
      "type": "integer",
      "minimum": 3
    },
    "mismatch_count": {
      "type": "integer",
      "minimum": 0
    },
    "artifacts": {
      "type": "array",
      "minItems": 3,
      "items": {
        "$ref": "#/$defs/artifact_verification_record"
      }
    }
  },
  "$defs": {
    "sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "artifact_verification_record": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "artifact_role",
        "candidate_id",
        "expected_sha256",
        "actual_sha256",
        "sha256_matches",
        "expected_byte_count",
        "actual_byte_count",
        "byte_count_matches",
        "verified"
      ],
      "properties": {
        "artifact_role": {
          "enum": ["baseline_run", "candidate_run", "qrels"]
        },
        "candidate_id": {
          "oneOf": [
            {"type": "null"},
            {"type": "string", "minLength": 1}
          ]
        },
        "expected_sha256": {
          "$ref": "#/$defs/sha256"
        },
        "actual_sha256": {
          "$ref": "#/$defs/sha256"
        },
        "sha256_matches": {
          "type": "boolean"
        },
        "expected_byte_count": {
          "type": "integer",
          "minimum": 0
        },
        "actual_byte_count": {
          "type": "integer",
          "minimum": 0
        },
        "byte_count_matches": {
          "type": "boolean"
        },
        "verified": {
          "type": "boolean"
        }
      }
    }
  }
}''',
    )


def harden_verification_json() -> None:
    """Reject duplicate names and non-standard numbers in persisted JSON."""
    cli_path = "src/rankweave/cli.py"
    content = read(cli_path)
    if "def _reject_nonstandard_json_number(" not in content:
        marker = "\ndef build_parser() -> argparse.ArgumentParser:\n"
        addition = '''

def _reject_nonstandard_json_number(raw_value: str) -> Any:
    """Reject NaN and infinity spellings that RFC 8259 excludes."""
    raise ValueError(
        f"report JSON contains non-standard number {raw_value!r}"
    )


def _reject_duplicate_json_names(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build one object while rejecting ambiguous duplicate member names."""
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(
                f"report JSON contains duplicate object name {name!r}"
            )
        result[name] = value
    return result


def _load_report_json(text: str) -> Any:
    """Parse one interoperable RFC 8259 report JSON value."""
    return json.loads(
        text,
        parse_constant=_reject_nonstandard_json_number,
        object_pairs_hook=_reject_duplicate_json_names,
    )
'''
        if marker not in content:
            raise SystemExit("missing CLI parser marker")
        content = content.replace(marker, addition + marker, 1)
    content = content.replace(
        'choices=("pairwise", "family"),',
        'choices=("pairwise", "family", "verification"),',
        1,
    )
    content = content.replace(
        "report_data = json.loads(report_artifact.text)",
        "report_data = _load_report_json(report_artifact.text)",
        1,
    )
    write(cli_path, content)


def install_tests() -> None:
    """Add strict parsing and verification-schema regression contracts."""
    report_test_path = "tests/test_report_schemas.py"
    report_tests = read(report_test_path)
    if 'report_type="verification"' not in report_tests:
        old = '''    ReportSchemaDescriptor(
        report_type="family",
        schema_version="v2",
        transport_schema_id="rankweave.trec-family-comparison.v2",
        resource_name="trec-family-comparison-v2.schema.json",
    ),
)'''
        new = '''    ReportSchemaDescriptor(
        report_type="family",
        schema_version="v2",
        transport_schema_id="rankweave.trec-family-comparison.v2",
        resource_name="trec-family-comparison-v2.schema.json",
    ),
    ReportSchemaDescriptor(
        report_type="verification",
        schema_version="v1",
        transport_schema_id="rankweave.artifact-verification.v1",
        resource_name="artifact-verification-v1.schema.json",
    ),
)'''
        if old not in report_tests:
            raise SystemExit("missing report schema descriptor test anchor")
        report_tests = report_tests.replace(old, new, 1)
    write(report_test_path, report_tests)

    schema_cli_path = "tests/test_schema_cli.py"
    schema_cli_tests = read(schema_cli_path)
    first_matrix = '''        ("pairwise", "v1"),
        ("pairwise", "v2"),
        ("family", "v1"),
        ("family", "v2"),
    ],'''
    if '("verification", "v1")' not in schema_cli_tests:
        schema_cli_tests = schema_cli_tests.replace(
            first_matrix,
            first_matrix.replace(
                '        ("family", "v2"),\n',
                '        ("family", "v2"),\n'
                '        ("verification", "v1"),\n',
            ),
            1,
        )
    write(schema_cli_path, schema_cli_tests)

    write(
        "tests/test_strict_verification_json.py",
        '''"""Fail-closed persisted-report JSON parsing contracts."""

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
''',
    )
    write(
        "tests/test_verification_schema.py",
        '''"""Machine-readable artifact-verification transport contracts."""

import copy
import hashlib

import pytest
from jsonschema import Draft202012Validator, ValidationError

from rankweave import load_report_schema, load_report_schema_text


def _record(role, payload, candidate_id=None):
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "artifact_role": role,
        "candidate_id": candidate_id,
        "expected_sha256": digest,
        "actual_sha256": digest,
        "sha256_matches": True,
        "expected_byte_count": len(payload),
        "actual_byte_count": len(payload),
        "byte_count_matches": True,
        "verified": True,
    }


def _verification_document():
    return {
        "schema_version": "rankweave.artifact-verification.v1",
        "rankweave_version": "0.14.0",
        "report_schema_version": "rankweave.trec-comparison.v2",
        "verified": True,
        "artifact_count": 3,
        "mismatch_count": 0,
        "artifacts": [
            _record("baseline_run", b"baseline"),
            _record("candidate_run", b"candidate"),
            _record("qrels", b"qrels"),
        ],
    }


def test_verification_schema_is_packaged_and_meta_schema_valid():
    """Expose canonical Draft 2020-12 verification schema text and data."""
    text = load_report_schema_text("verification", "v1")
    schema = load_report_schema("verification", "v1")

    assert text.endswith("\\n")
    assert schema["properties"]["schema_version"]["const"] == (
        "rankweave.artifact-verification.v1"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_verification_document())


def test_verification_v2_selector_fails_as_unsupported_combination():
    """Distinguish a known type from a nonexistent transport version."""
    with pytest.raises(ValueError, match="schema combination is unsupported"):
        load_report_schema_text("verification", "v2")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.update(extra="forbidden"),
        lambda document: document["artifacts"][0].update(
            expected_sha256="not-a-digest"
        ),
        lambda document: document.update(mismatch_count=-1),
    ],
)
def test_verification_schema_rejects_representative_violations(mutation):
    """Reject extra fields, malformed digests, and negative counts."""
    document = copy.deepcopy(_verification_document())
    mutation(document)

    with pytest.raises(ValidationError):
        Draft202012Validator(
            load_report_schema("verification", "v1")
        ).validate(document)
''',
    )


def update_documentation() -> None:
    """Synchronize release, architecture, usage, and standards documentation."""
    changelog = read("CHANGELOG.md")
    if "## [0.14.0]" not in changelog:
        section = '''## [0.14.0] — 2026-08-05

### Added
- Pure standard-library `verify_report_artifacts` APIs for exact pairwise and candidate-family v2 input verification.
- The `rankweave verify-artifacts` console and module command with deterministic JSON, exit `0` for a match, exit `1` for an evidence mismatch, and stderr-only exit `2` for invalid input.
- A strict JSON Schema Draft 2020-12 resource for `rankweave.artifact-verification.v1` and installed-wheel command/resource smoke tests.

### Changed
- Persisted reports are parsed as interoperable RFC 8259 JSON: duplicate member names and non-standard `NaN` or infinity numbers fail closed.
- Candidate-family verification requires report, evidence, and caller-supplied candidate order to agree exactly.

### Security
- Verification output excludes local paths and artifact payloads and compares both SHA-256 and raw byte counts.
- A successful comparison is explicitly not producer authentication, signature or provenance verification, an attestation, or a SLSA-level claim.

'''
        anchor = "## [0.13.0] — 2026-08-05\n"
        if anchor not in changelog:
            raise SystemExit("missing changelog release anchor")
        write("CHANGELOG.md", changelog.replace(anchor, section + anchor, 1))

    append_once(
        "README.md",
        "## Verify persisted artifact evidence",
        '''## Verify persisted artifact evidence

RankWeave 0.14.0 can compare explicit local files with the unsigned SHA-256 and raw byte-count evidence in a persisted v2 report without exposing file paths or payloads:

```bash
rankweave verify-artifacts \\
  --report comparison.json \\
  --baseline-run baseline.run \\
  --candidate-run candidate.run \\
  --qrels qrels.txt
```

Candidate-family verification uses ordered, repeatable `--candidate ID=PATH` arguments. Exit status `0` means all bytes match, `1` means at least one artifact differs, and `2` means the command or evidence is invalid. A match is an integrity comparison only—not authentication, signature verification, provenance verification, or a SLSA claim.''',
    )
    append_once(
        "docs/cli.md",
        "## `verify-artifacts`",
        '''## `verify-artifacts`

Use `verify-artifacts` only with pairwise or candidate-family v2 reports, because v1 reports intentionally contain no artifact evidence. The report is strict UTF-8 RFC 8259 JSON; duplicate object names, `NaN`, and infinity spellings are rejected. Every file uses the same bounded-read ceiling.

```bash
rankweave verify-artifacts \\
  --report family.json \\
  --baseline-run baseline.run \\
  --candidate lexical=lexical.run \\
  --candidate hybrid=hybrid.run \\
  --qrels qrels.txt \\
  --pretty
```

The JSON result is versioned as `rankweave.artifact-verification.v1`. It contains expected and observed SHA-256 digests, byte counts, independent match flags, and no local paths or input text.''',
    )
    append_once(
        "docs/report-schemas.md",
        "## Artifact-verification transport",
        '''## Artifact-verification transport

`rankweave schema --report-type verification --schema-version v1` emits the packaged Draft 2020-12 contract for `rankweave.artifact-verification.v1`. The schema is structurally strict and documents cross-field invariants that the producer and verification core enforce. Structural conformance alone is not evidence that the report producer or artifact source is trusted.''',
    )
    append_once(
        "ARCHITECTURE.md",
        "## Exact artifact-verification boundary",
        '''## Exact artifact-verification boundary

`artifact_verification.py` is a pure bytes-and-mappings core with no filesystem, JSON, provider, network, or database access. `cli.py` is the bounded filesystem and strict RFC 8259 boundary. The output transport is path-free and independently reusable by naruon or another MSA consumer. SHA-256 equality is deliberately separated from authentication and provenance policy.''',
    )
    append_once(
        "AGENTS.md",
        "## RankWeave 0.14 verification gate",
        '''## RankWeave 0.14 verification gate

Changes to artifact verification must preserve raw-byte hashing, independent digest and byte-count comparison, exact family order, path/payload non-disclosure, strict persisted JSON, console/module parity, the packaged verification schema, and 100% production statement and branch coverage. Do not describe a digest match as authentication, attestation, provenance verification, or a SLSA level.''',
    )
    append_once(
        "CLAUDE.md",
        "## Artifact verification",
        '''## Artifact verification

Keep the verification core standard-library-only and transport-neutral. Filesystem and JSON concerns belong in the CLI adapter. A mismatch is a normal machine-readable exit-1 result; malformed evidence remains stderr-only exit 2. Every new output field requires schema, docs, wheel-smoke, and coverage updates.''',
    )
    append_once(
        "docs/research/README.md",
        "### Artifact integrity and JSON interoperability",
        '''### Artifact integrity and JSON interoperability

Bray, T. (2017). *The JavaScript Object Notation (JSON) Data Interchange Format* (RFC 8259). RFC Editor. https://doi.org/10.17487/RFC8259

National Institute of Standards and Technology. (2015). *Secure Hash Standard (SHS)* (FIPS PUB 180-4). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.180-4

Supply-chain Levels for Software Artifacts. (n.d.). *Build: Verifying artifacts (SLSA specification v1.2)*. OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts

RFC 8259 says object names should be unique for interoperable interpretation and excludes `NaN` and infinity from JSON numbers. FIPS 180-4 specifies SHA-256 for change detection; NIST has announced a future revision but FIPS 180-4 remains the published standard. SLSA v1.2 verification additionally requires trusted provenance/attestation checks and matching an attestation subject to the artifact digest, so RankWeave's unsigned local comparison makes no SLSA claim.''',
    )
    write(
        "docs/artifact-verification.md",
        '''# Exact report-artifact verification

RankWeave compares the exact raw bytes supplied by a caller with the SHA-256 and raw byte-count evidence in a pairwise or candidate-family v2 report. The pure core accepts mappings and immutable `bytes`; the CLI owns strict JSON parsing and bounded filesystem reads.

## Decision contract

- exit `0`: every artifact digest and byte count matches;
- exit `1`: the report and evidence are valid, but one or more artifacts differ;
- exit `2`: usage, filesystem, size, UTF-8, JSON, evidence-shape, or family-order failure.

A family report must preserve exactly the same candidate order in its result array, artifact-evidence array, and repeatable command arguments. Output never includes local paths, report payloads, TREC text, or host metadata.

## Trust boundary

A successful result means only that supplied bytes equal unsigned evidence embedded in the supplied report. It does not authenticate the report producer, validate a digital signature, establish trusted execution, verify provenance, emit an attestation, or establish a SLSA level. Those claims require independent roots of trust and signed provenance or verification attestations.''',
    )


def main() -> None:
    """Apply all final RankWeave 0.14.0 source and documentation changes."""
    install_report_schema_registry()
    harden_verification_json()
    install_tests()
    update_documentation()


if __name__ == "__main__":
    main()
