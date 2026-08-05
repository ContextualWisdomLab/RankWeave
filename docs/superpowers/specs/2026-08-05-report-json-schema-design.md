# Versioned report JSON Schema design

## Problem

RankWeave emits four stable report transports:

- `rankweave.trec-comparison.v1`
- `rankweave.trec-comparison.v2`
- `rankweave.trec-family-comparison.v1`
- `rankweave.trec-family-comparison.v2`

Their field order and semantics are documented and regression-tested inside the
project, but downstream buyers do not receive machine-readable schemas. A shell,
CI, data warehouse, workflow engine, or another MSA component must either trust
unvalidated JSON or duplicate RankWeave's transport contract. That weakens
integration safety and makes schema drift difficult to detect before production.

## Decision

Ship strict JSON Schema Draft 2020-12 documents inside the wheel and expose them
through both a small Python API and a `rankweave schema` command.

```bash
rankweave schema --report-type pairwise --schema-version v2
```

```bash
python -m rankweave schema \
  --report-type family \
  --schema-version v1
```

The command emits the exact packaged schema as UTF-8 JSON followed by one
newline. Console and module entrypoints remain byte-identical.

## Why JSON Schema Draft 2020-12

JSON Schema's current published specification is Draft 2020-12. It defines a
JSON media type for structure, validation, documentation, and interaction
contracts. The validation vocabulary provides the assertion keywords needed by
RankWeave, including `type`, `required`, `properties`, numeric bounds, string
patterns, arrays, `const`, `enum`, and `additionalProperties`.

Three approaches were considered:

1. **Documentation only.** Smallest change, but buyers still duplicate the
   contract and cannot automate validation.
2. **Ship schemas only.** Machine-readable, but consumers must discover wheel
   resource paths and write Python glue.
3. **Ship schemas plus Python and CLI discovery.** Slightly larger surface but
   supports Python, shell, container, CI, and MSA consumers without embedding a
   runtime validator.

Approach 3 is selected. A bundled validator is intentionally excluded: a
complete standards-conformant JSON Schema implementation would add a runtime
dependency or create an unsafe partial validator. RankWeave remains
standard-library-only and lets consumers choose their validator.

## Package layout

```text
src/rankweave/report_schemas.py
src/rankweave/schemas/__init__.py
src/rankweave/schemas/trec-comparison-v1.schema.json
src/rankweave/schemas/trec-comparison-v2.schema.json
src/rankweave/schemas/trec-family-comparison-v1.schema.json
src/rankweave/schemas/trec-family-comparison-v2.schema.json
```

Hatchling includes these resources in the wheel. Package smoke tests inspect the
wheel and load each schema from an installed environment outside the source
tree.

## Public Python API

```python
from rankweave import available_report_schemas, load_report_schema

for descriptor in available_report_schemas():
    print(descriptor.report_type, descriptor.schema_version)

schema = load_report_schema("pairwise", "v2")
```

`ReportSchemaDescriptor` is a frozen record containing:

- `report_type`: `pairwise` or `family`;
- `schema_version`: `v1` or `v2`;
- `transport_schema_id`: the corresponding RankWeave JSON `schema_version`;
- `resource_name`: the packaged JSON resource.

`available_report_schemas()` returns a fixed tuple in pairwise-v1, pairwise-v2,
family-v1, family-v2 order.

`load_report_schema_text()` returns the exact packaged UTF-8 schema text with one
trailing newline. `load_report_schema()` parses and returns a fresh dictionary
so caller mutation never alters subsequent loads. Unknown report types or
versions fail closed with stable `ValueError` messages.

## CLI contract

The `schema` subcommand requires:

- `--report-type pairwise|family`
- `--schema-version v1|v2`

No network, package registry, database, benchmark, or filesystem input is used.
The command writes the packaged schema to stdout as UTF-8 bytes and exits `0`.
Usage failures retain RankWeave's stderr-only exit-2 contract.

No `--pretty` flag is needed because packaged schemas use one canonical,
human-readable serialization. Consumers needing compact storage can transform
the JSON without changing its semantics.

## Schema identity and strictness

Each schema contains:

- `$schema`: `https://json-schema.org/draft/2020-12/schema`;
- stable `$id` using a `urn:contextualwisdomlab:rankweave:` namespace;
- `title` and `description`;
- exact `schema_version` through `const`;
- complete `required` arrays;
- `additionalProperties: false` for every object;
- finite-domain numeric constraints where JSON Schema can express them;
- supported metric, alternative, and method enums;
- SHA-256 pattern `^[0-9a-f]{64}$` and non-negative byte counts for v2;
- strict query-difference and candidate records;
- `$defs` for reusable nested structures.

JSON Schema cannot express all RankWeave invariants. It cannot require
`candidate_count` to equal the candidate-array length, align query IDs across
records, enforce candidate ordering semantics, or reject IEEE non-finite values
that are not valid JSON numbers anyway. `$comment` documents cross-field
invariants that remain guaranteed by RankWeave generation and should be checked
by domain-aware consumers when accepting third-party JSON.

## Validation and testing

The runtime package remains dependency-free. The development extra adds the
reference Python `jsonschema` implementation solely for tests.

Tests must:

1. use `Draft202012Validator.check_schema` on all four resources;
2. generate real pairwise and family v1/v2 reports through the CLI and validate
   them against their packaged schemas;
3. mutate reports to prove missing fields, extra fields, invalid enums, invalid
   digest patterns, and negative byte counts are rejected;
4. prove API order, immutable descriptors, fresh dictionaries, trailing newline,
   and stable error messages;
5. prove console and module schema commands are byte-identical;
6. inspect the built wheel for all resources and load them after isolated
   installation;
7. preserve Python 3.10-3.13, Ruff, production docstrings, 100% production
   statement and branch coverage, Security Scan, and Semgrep.

## Standards and evidence boundary

The feature is grounded in the JSON Schema Core and Validation specifications,
Draft 2020-12. The project documents those sources in APA 7th edition form.

A schema proves structural conformance only. It does not authenticate a report,
prove that the reported metrics were computed by RankWeave, validate artifact
hashes against external files, or establish scientific validity. Those claims
remain separate and must not be inferred from successful schema validation.

## Compatibility

The four report transports do not change. This feature publishes their existing
contracts. The standalone package, console command, module entrypoint, and
naruon/MSA consumption model remain supported. No database, UI, LLM, or
Psychometrics arithmetic is introduced.

## Release

This additive integration surface is RankWeave 0.13.0. Synchronize
`pyproject.toml`, `rankweave.__version__`, version tests, installed-wheel smoke
assertions, README, CLI documentation, `AGENTS.md`, research references, and
`CHANGELOG.md`. No tag, GitHub Release, or package publication occurs before
protected merge.
