# RankWeave report JSON Schemas

## Available contracts

RankWeave 0.13.0 ships four JSON Schema Draft 2020-12 resources:

| Report type | Version | Transport identifier |
|---|---|---|
| pairwise | v1 | `rankweave.trec-comparison.v1` |
| pairwise | v2 | `rankweave.trec-comparison.v2` |
| family | v1 | `rankweave.trec-family-comparison.v1` |
| family | v2 | `rankweave.trec-family-comparison.v2` |

The v1 contracts remain the default report transports. V2 is opt-in through
`--include-artifact-digests` and adds exact-byte SHA-256 and byte-count evidence.

## Discovery

```bash
rankweave schema --report-type pairwise --schema-version v1
python -m rankweave schema --report-type family --schema-version v2
```

```python
from rankweave import available_report_schemas, load_report_schema

for descriptor in available_report_schemas():
    schema = load_report_schema(
        descriptor.report_type,
        descriptor.schema_version,
    )
```

`load_report_schema_text` returns canonical packaged UTF-8 text with one trailing
newline. `load_report_schema` returns a fresh dictionary on every call. Unknown
selectors fail closed.

## Validation boundary

RankWeave intentionally has no runtime validator dependency. Consumers should
validate with a conforming Draft 2020-12 implementation. The development suite
uses the reference Python `jsonschema` package to check every schema and real
generated v1/v2 report.

The schemas reject missing fields, additional object properties, unsupported
metrics and alternatives, malformed SHA-256 values, and invalid numerical
domains. `$comment` records cross-field invariants that remain the responsibility
of RankWeave generation or a domain-aware consumer.

Structural conformance is not producer authentication, digital signature
verification, external artifact-digest verification, trusted-execution evidence,
or scientific validation.

## Compatibility policy

Published schema resources are immutable descriptions of their transport
identifiers. Additive package releases may retain the same schema resources. An
incompatible transport change requires a new transport identifier, new packaged
schema, complete regression coverage, installed-wheel smoke, documentation, and
release notes.
