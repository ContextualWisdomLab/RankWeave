# Exact report-artifact verification design

## Problem

RankWeave 0.12.0 added optional SHA-256 and raw byte-count evidence to pairwise
and candidate-family v2 reports. RankWeave 0.13.0 publishes machine-readable
schemas for those reports. A consumer can therefore inspect the expected digest,
but still has to write custom glue to answer the operational question:

> Do these local baseline, candidate, and qrels files exactly match the bytes
> named by this persisted RankWeave report?

Custom verification logic is easy to get wrong. Consumers may hash decoded text
instead of source bytes, silently reorder a candidate family, compare only the
hash but not the byte count, leak local paths in logs, accept a v1 report that
contains no artifact evidence, or mistake a digest match for report authenticity.

## Decision

Add a pure, standard-library-only verification core and a `rankweave
verify-artifacts` command. Verification is available only for the existing v2
pairwise and candidate-family report transports because v1 intentionally has no
artifact evidence.

The command accepts one persisted report plus explicit local artifacts:

```bash
rankweave verify-artifacts \
  --report comparison.json \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt
```

```bash
rankweave verify-artifacts \
  --report family-comparison.json \
  --baseline-run baseline.run \
  --candidate lexical=lexical.run \
  --candidate hybrid=hybrid.run \
  --qrels qrels.txt
```

The command writes one versioned UTF-8 JSON verification document. It exits:

- `0` when every supplied artifact matches;
- `1` when the report is structurally usable but at least one digest or byte
  count differs;
- `2` for usage, filesystem, size, UTF-8, JSON, evidence-shape, or candidate
  alignment errors.

A mismatch is an expected verification outcome, not a parser failure, so it is
reported as JSON rather than stderr-only text.

## Architecture

### Pure verification core

Create `src/rankweave/artifact_verification.py`. The core accepts a parsed report
mapping and immutable raw `bytes`. It performs no filesystem, JSON parsing,
network, database, provider, or command-line work.

Public records:

- `ArtifactVerificationRecord` — one role, optional candidate identifier,
  expected and observed SHA-256, expected and observed byte count, and match
  booleans.
- `ArtifactVerificationReport` — source report schema identifier and an ordered
  tuple of verification records, with derived `verified` and `mismatch_count`
  properties.

Public function:

```python
verify_report_artifacts(
    report,
    *,
    baseline_run_bytes,
    qrels_bytes,
    candidate_run_bytes=None,
    candidate_run_bytes_by_id=None,
)
```

The core recognizes only:

- `rankweave.trec-comparison.v2`;
- `rankweave.trec-family-comparison.v2`.

It rejects v1 and unknown transports.

### CLI adapter

`src/rankweave/cli.py` remains the filesystem boundary. A shared bounded binary
reader performs the pre-read size check and the `max_input_bytes + 1` read. Text
inputs decode the same bytes as strict UTF-8. Verification never reads an
artifact twice.

The report itself is strict UTF-8 JSON and subject to the same configurable
per-file ceiling. No local path is included in success or mismatch JSON.

## Verification contracts

### Pairwise

The report `artifacts` object must have exactly:

- `baseline_run`;
- `candidate_run`;
- `qrels`.

The caller must supply `candidate_run_bytes` and must not supply a candidate
mapping.

Output order is baseline, candidate, qrels.

### Candidate family

The report `artifacts` object must have exactly:

- `baseline_run`;
- `qrels`;
- ordered `candidates`.

Each candidate evidence object must contain exactly `candidate_id`, `sha256`,
and `byte_count`. Candidate identifiers must be non-empty, printable, free of
`=`, and free of surrounding whitespace. They must be unique.

The following three orders must agree exactly:

1. the top-level report `candidates` array;
2. the artifact-evidence candidate array;
3. the caller-supplied mapping insertion order.

`candidate_count` must equal both report arrays. This prevents a digest from
being attributed to the wrong statistical candidate.

Output order is baseline, qrels, then candidates in declared family order.

## Evidence validation

Every expected artifact record must contain exactly:

```json
{
  "sha256": "64 lowercase hexadecimal characters",
  "byte_count": 1234
}
```

`byte_count` is a non-negative integer and booleans are rejected. SHA-256 is
computed over the exact supplied raw bytes with Python's standard-library
`hashlib.sha256`.

The verifier compares both digest and byte count independently. A record is
verified only when both match. Reporting both results helps diagnose truncated,
re-encoded, or otherwise substituted files without weakening the decision rule.

## Output transport

The stable identifier is:

```text
rankweave.artifact-verification.v1
```

Top-level field order:

1. `schema_version`
2. `rankweave_version`
3. `report_schema_version`
4. `verified`
5. `artifact_count`
6. `mismatch_count`
7. `artifacts`

Each artifact entry contains:

1. `artifact_role`
2. `candidate_id` (`null` except candidate-family members)
3. `expected_sha256`
4. `actual_sha256`
5. `sha256_matches`
6. `expected_byte_count`
7. `actual_byte_count`
8. `byte_count_matches`
9. `verified`

The output intentionally contains no path, report payload, TREC text, or local
host metadata.

## Security and standards boundary

FIPS 180-4 remains the current NIST specification used by CAVP for SHA-2,
although NIST has announced a future revision. RankWeave uses SHA-256 only as an
exact-byte integrity comparison.

SLSA v1.2 verification guidance requires matching an attestation subject digest
to the artifact in question, while also requiring signature and trust checks for
a provenance or verification attestation. RankWeave implements only the narrow
local byte-to-digest comparison. It does not verify a signature, producer,
builder identity, root of trust, provenance policy, or SLSA level.

The verifier must therefore never label its output an attestation or claim
artifact authenticity. A verified result means only that the supplied bytes
match the unsigned digest evidence inside the supplied RankWeave report.

## Testing

Test-driven coverage must include:

- pairwise all-match result;
- pairwise digest mismatch;
- pairwise byte-count mismatch with equal supplied digest evidence constructed
  for the test;
- family all-match result and stable order;
- family candidate mismatch;
- v1 rejection;
- unknown report transport rejection;
- malformed artifact object keys;
- malformed SHA-256 and byte count;
- booleans rejected as counts;
- missing, duplicate, reordered, and extra family candidates;
- top-level and evidence candidate-order disagreement;
- wrong pairwise/family input mode;
- non-bytes API inputs;
- bounded report and artifact reads;
- strict UTF-8 and malformed JSON;
- no local path in JSON output;
- console/module byte parity;
- mismatch exit `1`, success exit `0`, usage/error exit `2`;
- installed-wheel smoke for pairwise and family verification;
- production statement and branch coverage 100% on Python 3.10–3.13.

## Release

This additive buyer-visible workflow is RankWeave 0.14.0. Synchronize package
metadata, public version, version regression test, installed-wheel assertions,
README, CLI and verification documentation, `AGENTS.md`, architecture,
standards references, and `CHANGELOG.md`. Do not create a tag, GitHub Release,
package publication, signature, attestation, or SLSA claim before protected
merge.
