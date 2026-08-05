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

### Pairwise success schema

Success emits one UTF-8 JSON document followed by a newline. The stable schema
identifier is:

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

### Candidate-family success schema

Success emits one UTF-8 JSON document with schema identifier:

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
then read with an explicit `max_input_bytes + 1` ceiling. The second check
rejects a file that grows after its initial size observation without first
loading an unbounded payload. The default limit is 64 MiB **per artifact** and
can be lowered by the caller. A ceiling that cannot be represented by the
platform binary-read API becomes an expected validation failure.

The commands are synchronous. A service accepting untrusted uploads should
apply its own request timeout, tenant quota, filesystem isolation, concurrency
limit, and durable-job policy before invoking RankWeave.

## CI examples

Pairwise comparison:

```bash
set -euo pipefail

rankweave compare \
  --baseline-run artifacts/baseline.run \
  --candidate-run artifacts/candidate.run \
  --qrels artifacts/qrels.txt \
  --cutoff 20 \
  --alternative candidate-greater \
  --pretty > artifacts/comparison.json
```

Candidate-family comparison:

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
  --pretty > artifacts/family-comparison.json
```

A deployment gate should combine held-out retrieval effect, uncertainty,
latency, cost, safety, and product-value thresholds. Neither a raw nor an
adjusted p-value is sufficient by itself.

## Compatibility

The JSON schemas are versioned independently from the package. Additive package
releases may retain the `v1` identifiers; an incompatible transport change
requires a new schema identifier. Full parsed TREC artifacts and immutable
comparison reports remain available through the Python API rather than being
reconstructed from the CLI projections.
