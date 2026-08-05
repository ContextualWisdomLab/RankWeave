# RankWeave command-line interface

RankWeave installs a dependency-free `rankweave` command for strict TREC
comparison workflows. The CLI is a thin transport adapter over the Python API:

- `rankweave compare` delegates to `compare_trec_runs`;
- `rankweave compare-family` delegates to `compare_trec_run_family`.

It does not maintain separate TREC parsing, effectiveness metrics,
query-alignment, randomization, or Holm-adjustment logic.

## Pairwise comparison

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10
```

The module entrypoint is equivalent:

```bash
python -m rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10
```

### Pairwise v1 success schema

The default emits one UTF-8 JSON document with schema identifier:

```text
rankweave.trec-comparison.v1
```

Top-level fields are emitted in this order:

1. `schema_version`
2. `rankweave_version`
3. `baseline_run_id`
4. `candidate_run_id`
5. `cutoff`
6. `metric_name`
7. `alternative`
8. `query_count`
9. `nonzero_difference_count`
10. `baseline_mean`
11. `candidate_mean`
12. `mean_difference`
13. `p_value`
14. `method`
15. `randomizations_evaluated`
16. `random_seed`
17. `query_differences`

Each `query_differences` entry contains `query_id`, `baseline_value`,
`candidate_value`, and candidate-minus-baseline `difference`.

## Candidate-family comparison

Use an explicitly ordered family when several candidate systems are compared
with one baseline and one qrels artifact:

```bash
rankweave compare-family \
  --baseline-run baseline.run \
  --candidate lexical=artifacts/lexical.run \
  --candidate hybrid=artifacts/hybrid.run \
  --candidate reranked=artifacts/reranked.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --alternative candidate-greater \
  --familywise-alpha 0.05
```

The equivalent module invocation is:

```bash
python -m rankweave compare-family \
  --baseline-run baseline.run \
  --candidate lexical=artifacts/lexical.run \
  --candidate hybrid=artifacts/hybrid.run \
  --qrels qrels.txt \
  --cutoff 10
```

`--candidate` is repeatable. Its first `=` separates a non-empty candidate
identifier from the local path, so later `=` characters remain part of the
path. Candidate identifiers must be unique, printable Unicode strings that do
not contain `=` or leading or trailing whitespace. Command-line order is
preserved as statistical-family and tie-breaking evidence; RankWeave never
discovers candidates by scanning a directory.

### Candidate-family v1 success schema

The default emits one UTF-8 JSON document with schema identifier:

```text
rankweave.trec-family-comparison.v1
```

Top-level fields are emitted in this order:

1. `schema_version`
2. `rankweave_version`
3. `baseline_run_id`
4. `cutoff`
5. `metric_name`
6. `alternative`
7. `familywise_alpha`
8. `candidate_count`
9. `candidates`

Each candidate entry contains:

1. `candidate_id`
2. `candidate_run_id`
3. `query_count`
4. `nonzero_difference_count`
5. `baseline_mean`
6. `candidate_mean`
7. `mean_difference`
8. `raw_p_value`
9. `holm_adjusted_p_value`
10. `rejected_at_familywise_alpha`
11. `method`
12. `randomizations_evaluated`
13. `random_seed`
14. `query_differences`

Candidate and query order remain the immutable Python API order. Unicode
identifiers are emitted directly rather than as ASCII escape sequences.

Holm adjustment controls false rejection across the candidate family supplied
before results are inspected. It does not measure effect size, operational
value, latency, cost, safety, or permission to deploy a candidate.

## Exact input-artifact evidence

Add `--include-artifact-digests` when a stored report must be bound to the exact
run and qrels bytes that produced it:

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests > comparison.json
```

```bash
rankweave compare-family \
  --baseline-run baseline.run \
  --candidate lexical=lexical.run \
  --candidate hybrid=hybrid.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests > family-comparison.json
```

The flag changes the schema identifier because existing consumers may enforce
an exact v1 field set and order:

- pairwise: `rankweave.trec-comparison.v2`;
- candidate family: `rankweave.trec-family-comparison.v2`.

Both v2 schemas insert `artifacts` immediately after `rankweave_version`.
Every evidence record contains:

```json
{
  "sha256": "64 lowercase hexadecimal characters",
  "byte_count": 1234
}
```

Pairwise `artifacts` contains `baseline_run`, `candidate_run`, and `qrels`.
Family `artifacts` contains `baseline_run`, `qrels`, and an ordered `candidates`
array. Every candidate evidence entry contains its explicit `candidate_id`,
`sha256`, and `byte_count`.

The digest is computed over the exact bytes read before UTF-8 decoding. Comments,
line endings, trailing whitespace, and different Unicode byte sequences
therefore affect artifact identity even when TREC evaluation ignores or
normalizes some of those distinctions. `byte_count` is the raw byte length, not
Unicode character count.

Local input paths are deliberately excluded. A report can cross machines,
containers, tenants, and organizations without disclosing mutable filesystem
locations.

SHA-256 evidence supports later byte-for-byte verification, but it does not
authenticate the report producer, sign the report, prove trusted execution, or
establish a SLSA level. Consumers needing authenticity must protect or sign the
report and independently acquire the artifacts being verified.

### Verification example

```python
import hashlib
import json
from pathlib import Path

report = json.loads(Path("comparison.json").read_text(encoding="utf-8"))
expected = report["artifacts"]["candidate_run"]
actual_bytes = Path("candidate.run").read_bytes()

assert len(actual_bytes) == expected["byte_count"]
assert hashlib.sha256(actual_bytes).hexdigest() == expected["sha256"]
```

## Emit machine-readable report schemas

The installed package exposes each stable report contract as canonical UTF-8
JSON Schema Draft 2020-12 text:

```bash
rankweave schema \
  --report-type pairwise \
  --schema-version v2 > pairwise-v2.schema.json
```

```bash
python -m rankweave schema \
  --report-type family \
  --schema-version v1 > family-v1.schema.json
```

`--report-type` accepts `pairwise` or `family`; `--schema-version` accepts `v1`
or `v2`. The command reads only packaged resources, performs no network or
filesystem input access, writes one canonical UTF-8 JSON document, and retains
the stderr-only exit-2 usage contract. Console and module output are
byte-identical.

The runtime deliberately does not provide a partial validator. Use a conforming
Draft 2020-12 implementation in the consuming service. A valid document has the
required structure; this alone does not authenticate its producer or verify its
statistical claims.

## Shared options

| Option | Required | Default | Contract |
|---|---:|---:|---|
| `--baseline-run` | yes | — | Strict UTF-8 six-column TREC run file. |
| `--qrels` | yes | — | Strict UTF-8 four-column qrels file. |
| `--cutoff` | yes | — | Positive ASCII decimal integer. |
| `--metric` | no | `ndcg_at_k` | A supported RankWeave comparison metric. |
| `--alternative` | no | `two-sided` | `two-sided`, `candidate-greater`, or `candidate-less`. |
| `--randomizations` | no | `10000` | Positive ASCII decimal integer. |
| `--seed` | no | `0` | Signed ASCII decimal integer. |
| `--max-input-bytes` | no | `67108864` | Positive per-artifact byte ceiling. |
| `--pretty` | no | false | Emit deterministic two-space JSON. |
| `--include-artifact-digests` | no | false | Emit path-free v2 SHA-256 and byte-count evidence. |

Pairwise comparison additionally requires `--candidate-run`. Candidate-family
comparison additionally requires one or more `--candidate ID=PATH` options and
accepts `--familywise-alpha`, which defaults to `0.05` and must be finite in
`(0, 1]`.

The CLI accepts local files only. It performs no URL fetch, decompression,
globbing, benchmark download, database access, or provider call. It does not
write an output file; redirect or capture stdout in the calling orchestration
layer.

## Output and failure contract

Compact JSON is the default. `--pretty` changes whitespace only. A successful
command writes exactly one UTF-8 encoded JSON document plus a newline to the
standard-output byte stream and exits with status `0`; the process locale or
text-stream encoding cannot change the transport encoding.

Expected usage, filesystem, UTF-8, size, TREC, evaluation, and statistical
validation failures write no stdout, emit one line to stderr, and return status
`2`:

```text
rankweave: error: <specific message>
```

Candidate-specific TREC or evaluation errors retain the candidate identifier
and the precise lower-level validation message. Unexpected programmer defects
are not converted into success-like JSON.

## Resource boundary

Every baseline, candidate, and qrels artifact is checked before reading and is
then read with an explicit `max_input_bytes + 1` ceiling. The same bounded byte
payload is hashed, counted, and strictly decoded once. The second size check
rejects a file that grows after its initial size observation without first
loading an unbounded payload. The default limit is 64 MiB **per artifact** and
can be lowered by the caller. A ceiling that cannot be represented by the
platform binary-read API becomes an expected validation failure.

The commands are synchronous. A service accepting untrusted uploads should
apply its own request timeout, tenant quota, filesystem isolation, concurrency
limit, and durable-job policy before invoking RankWeave.

## CI examples

Pairwise comparison with evidence:

```bash
set -euo pipefail

rankweave compare \
  --baseline-run artifacts/baseline.run \
  --candidate-run artifacts/candidate.run \
  --qrels artifacts/qrels.txt \
  --cutoff 20 \
  --alternative candidate-greater \
  --include-artifact-digests \
  --pretty > artifacts/comparison.json
```

Candidate-family comparison with evidence:

```bash
set -euo pipefail

rankweave compare-family \
  --baseline-run artifacts/baseline.run \
  --candidate model-a=artifacts/model-a.run \
  --candidate model-b=artifacts/model-b.run \
  --qrels artifacts/qrels.txt \
  --cutoff 20 \
  --alternative candidate-greater \
  --familywise-alpha 0.05 \
  --include-artifact-digests \
  --pretty > artifacts/family-comparison.json
```

A deployment gate should combine held-out retrieval effect, uncertainty,
latency, cost, safety, and product-value thresholds. Neither a raw nor an
adjusted p-value is sufficient by itself.

## Compatibility

The v1 schemas remain the default and are unchanged. V2 is opt-in and adds
artifact evidence while preserving all statistical field meanings. Schema
identifiers are versioned independently from the package; any future
incompatible transport change requires another identifier. Full parsed TREC
artifacts and immutable comparison reports remain available through the Python
API rather than being reconstructed from CLI projections.
