# RankWeave command-line interface

RankWeave installs a dependency-free `rankweave` command for strict pairwise
comparison of TREC run artifacts. The command is a thin adapter over
`compare_trec_runs`; it does not maintain separate parsing, metric, query
alignment, or randomization logic.

## Invocation

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

## Options

| Option | Required | Default | Contract |
|---|---:|---:|---|
| `--baseline-run` | yes | — | Strict UTF-8 TREC run file. |
| `--candidate-run` | yes | — | Strict UTF-8 TREC run file. |
| `--qrels` | yes | — | Strict UTF-8 four-column qrels file. |
| `--cutoff` | yes | — | Positive ASCII decimal integer. |
| `--metric` | no | `ndcg_at_k` | One of RankWeave's supported comparison metrics. |
| `--alternative` | no | `two-sided` | `two-sided`, `candidate-greater`, or `candidate-less`. |
| `--randomizations` | no | `10000` | Positive ASCII decimal integer. |
| `--seed` | no | `0` | Signed ASCII decimal integer. |
| `--max-input-bytes` | no | `67108864` | Positive per-artifact byte ceiling. |
| `--pretty` | no | false | Emit deterministic two-space JSON. |

The command does not accept URLs, compressed archives, benchmark downloads, or
shell expansion. It does not write an output file. Redirect or capture stdout in
the calling orchestration layer.

## Success output

Success writes one UTF-8 JSON document followed by a newline to stdout and
returns exit status `0`. Compact JSON is the default; `--pretty` changes only
whitespace.

The stable top-level schema identifier is:

```text
rankweave.trec-comparison.v1
```

Fields are emitted in this fixed order:

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
`candidate_value`, and candidate-minus-baseline `difference`. Unicode query
identifiers remain readable rather than being ASCII-escaped.

Example:

```json
{
  "schema_version": "rankweave.trec-comparison.v1",
  "rankweave_version": "0.10.0",
  "baseline_run_id": "baseline",
  "candidate_run_id": "candidate",
  "cutoff": 1,
  "metric_name": "ndcg_at_k",
  "alternative": "candidate-greater",
  "query_count": 1,
  "nonzero_difference_count": 1,
  "baseline_mean": 0.0,
  "candidate_mean": 1.0,
  "mean_difference": 1.0,
  "p_value": 0.5,
  "method": "exact",
  "randomizations_evaluated": 2,
  "random_seed": null,
  "query_differences": [
    {
      "query_id": "q",
      "baseline_value": 0.0,
      "candidate_value": 1.0,
      "difference": 1.0
    }
  ]
}
```

The example illustrates the transport contract, not a benchmark-quality claim.
Actual query evidence is retained in `query_differences`.

## Failure output

Expected usage, filesystem, UTF-8, size, TREC, evaluation, and statistical
validation failures return exit status `2`, write no stdout, and emit one line
to stderr:

```text
rankweave: error: <specific message>
```

Lower-level parser and comparison messages remain visible after the stable
prefix. Unexpected programmer errors are not converted into success-like JSON.

## Resource boundary

Each artifact is checked before reading and then read with an explicit
`max_input_bytes + 1` ceiling. The second check rejects a file that grows after
its initial size observation without first loading an unbounded payload into
memory. The default limit is 64 MiB per artifact and can be lowered by the
caller.

The CLI is intentionally synchronous. A service that accepts untrusted uploads
should enforce its own request timeout, tenant quota, filesystem isolation, and
job concurrency before invoking RankWeave.

## CI example

```bash
set -euo pipefail

rankweave compare \
  --baseline-run artifacts/baseline.run \
  --candidate-run artifacts/candidate.run \
  --qrels artifacts/qrels.txt \
  --cutoff 20 \
  --alternative candidate-greater \
  --pretty > artifacts/comparison.json

python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("artifacts/comparison.json").read_text(encoding="utf-8"))
assert report["schema_version"] == "rankweave.trec-comparison.v1"
print(report["mean_difference"], report["p_value"])
PY
```

A p-value is not a deployment gate by itself. Consumers should define practical
effect, latency, cost, safety, and held-out quality thresholds separately.

## Compatibility

The JSON schema is versioned independently from the package version. Additive
package releases may keep `rankweave.trec-comparison.v1`; an incompatible JSON
change requires a new schema identifier. Parsed TREC records and complete
internal dataclasses remain available through the Python API rather than being
reconstructed from the CLI projection.

Candidate-family CLI support is deliberately outside the `0.10.0` surface. Use
`compare_trec_run_family` from Python when Holm-adjusted family-wise evidence is
required.
