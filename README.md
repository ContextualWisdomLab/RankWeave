# RankWeave

**A leaf product for hybrid-retrieval fusion, evaluation, statistical
comparison, offline policy tuning, and strict TREC interchange.**

RankWeave is a pure-Python, standard-library-only library and command-line
tool. It fuses lexical, dense, learned-sparse, graph, and other retrieval
channels into deterministic rankings; evaluates those rankings; compares paired
systems; controls family-wise error across a named candidate family; selects
fixed fusion policies on validation evidence; and reads and writes standard
TREC artifacts.

It is a **leaf product**: it must run by itself, and a host may call it as a
published dependency. Those are the same product, not competing designs.

[Naruon](https://github.com/ContextualWisdomLab/naruon) is the intended
composition hub and may call RankWeave through the published package, CLI, and
report-schema contracts. That hub-and-leaf call is the supported integration
path; it is not a layering or MSA violation. RankWeave does not talk to a
database, embedding provider, search index, or benchmark download service, and
it does **not** require a Naruon checkout to install, run, or test.

The runtime imports only the Python standard library. Python 3.10+; Apache-2.0.

## What operators get

- **Fusion:** TM2C2 convex combination and reciprocal-rank fusion, including
  fixed channel-reliability weights.
- **Evaluation:** precision@k, recall@k, reciprocal-rank@k, and graded nDCG@k
  on complete query sets.
- **Comparison:** identifier-aligned paired randomization, plus Holm
  family-wise correction for an explicit candidate family.
- **Tuning and assessment:** validation-set policy selection, caller-owned
  blocked folds, and availability-time backtesting.
- **TREC interchange:** fail-closed four-column qrels and six-column runs.
- **Shell and CI transport:** versioned UTF-8 JSON reports, opt-in exact-byte
  artifact digests, and packaged JSON Schema contracts.

RankWeave never silently drops a query to inflate a metric. A p-value is not
effect size, practical significance, or permission to deploy.

## Run RankWeave alone

No host application, Naruon tree, database, or network service is required.

### Install

PyPI currently publishes only `0.1.0`. Check
[pypi.org/project/rankweave](https://pypi.org/project/rankweave/) for the live
index before assuming a newer version is public. Install the published
package:

```bash
python -m pip install rankweave==0.1.0
```

The wheel installs the `rankweave` package and the `rankweave` console command.
`python -m rankweave` is equivalent to the console script.

The reviewed source tree is currently `0.18.0`, and a GitHub Release exists for
it, but that version is **not yet on PyPI** (see
[`docs/releasing.md`](docs/releasing.md) for the open publication gap). For the
post-0.1.0 APIs documented below, install the exact reviewed commit or tag
instead of assuming the PyPI name already carries them:

```bash
python -m pip install "rankweave @ git+https://github.com/ContextualWisdomLab/RankWeave.git@v0.18.0"
```

```bash
git clone https://github.com/ContextualWisdomLab/RankWeave.git
cd RankWeave
python -m pip install .
```

See [`docs/releasing.md`](docs/releasing.md) for publisher identity and
attestation boundaries.

### Compare two TREC runs

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --alternative candidate-greater \
  --pretty > comparison.json
```

Success writes one UTF-8 JSON document and a newline to stdout and exits `0`.
Expected usage, file, UTF-8, size, TREC, evaluation, and statistical errors
write one `rankweave: error: ...` line to stderr, no stdout, and exit `2`.

The default schema is `rankweave.trec-comparison.v1`.

### Compare a named candidate family

```bash
rankweave compare-family \
  --baseline-run baseline.run \
  --candidate model-a=artifacts/model-a.run \
  --candidate model-b=artifacts/model-b.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --alternative candidate-greater \
  --familywise-alpha 0.05 \
  --pretty > family-comparison.json
```

Repeatable `--candidate ID=PATH` options define the complete family in
command-line order. RankWeave does not scan a directory to invent the family.
The default schema is `rankweave.trec-family-comparison.v1`.

### Bind and verify exact input bytes

Run tags are descriptive provenance and may repeat. Add
`--include-artifact-digests` when a persisted report must identify the exact
baseline, candidate, and qrels bytes that were evaluated. That opt-in path
emits `rankweave.trec-comparison.v2` or
`rankweave.trec-family-comparison.v2`. Local paths are never written.

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests > comparison.json
```

```bash
rankweave verify-artifacts \
  --report comparison.json \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt
```

Family verification uses the same ordered `--candidate ID=PATH` arguments.
Exit `0` means every digest and byte count matches, `1` means at least one
artifact differs, and `2` means the command or evidence is invalid. A match is
an integrity comparison only—not authentication, a signature check, provenance
verification, or a SLSA claim.

Inputs default to a 64 MiB limit **per artifact**. The same bounded payload is
hashed, counted, and strictly decoded once.

### Fuse, evaluate, and compare in Python

Fuse one lexical+dense candidate:

```python
from rankweave import FusionSettings, fuse_channel_scores

score = fuse_channel_scores(
    word_similarity_score=0.62,
    cosine_distance=0.30,
    channel_ranks={"lexical": 1, "dense": 1},
    settings=FusionSettings(),
)
```

Fuse complete score lists or rank-only lists:

```python
from rankweave import weighted_convex_fuse, weighted_reciprocal_rank_fuse

scored = weighted_convex_fuse(
    {
        "semantic": [("document-b", 0.90), ("document-a", 0.50)],
        "lexical": [("document-a", 0.80), ("document-c", 0.70)],
    },
    {"semantic": 0.60, "lexical": 0.40},
    limit=10,
)

ranked = weighted_reciprocal_rank_fuse(
    {
        "lexical": ["document-a", "document-b"],
        "dense": ["document-b", "document-c"],
    },
    {"lexical": 0.25, "dense": 0.75},
    limit=10,
)
```

Evaluate a complete ranking set. Ranking and judgment mappings must contain
exactly the same query IDs:

```python
from rankweave import evaluate_rankings

report = evaluate_rankings(
    {
        "query-a": ["document-a", "document-b"],
        "query-b": ["document-c"],
    },
    {
        "query-a": {"document-a": 3, "document-b": 1},
        "query-b": {"document-c": 2},
    },
    cutoff=10,
)

print(report.aggregate.mean_ndcg_at_k)
```

nDCG uses gain `2**relevance - 1`. That is not claimed to be numerically
identical to `trec_eval`'s default identity-gain configuration.

Compare a candidate with a baseline. Values join by query identifier, never
tuple position:

```python
from rankweave import CANDIDATE_GREATER_ALTERNATIVE, compare_rankings

comparison = compare_rankings(
    {"q": ["irrelevant", "relevant"]},
    {"q": ["relevant", "irrelevant"]},
    {"q": {"relevant": 1}},
    cutoff=1,
    alternative=CANDIDATE_GREATER_ALTERNATIVE,
)

print(comparison.significance.mean_difference)
print(comparison.significance.p_value)
```

For up to 16 non-zero query differences, RankWeave enumerates all sign
assignments exactly. Larger comparisons use deterministic local Monte Carlo
randomization with a plus-one p-value correction.

Parse and compare TREC artifacts without a host:

```python
from rankweave import compare_trec_runs, evaluate_trec_run, parse_trec_qrels, parse_trec_run

qrels_text = """\
# topic judgments
q1 0 document-a 2
q1 0 document-b 0
"""
run_text = """\
q1 Q0 document-a 1 0.93 NIST-run_1
q1 Q0 document-b 2 0.42 NIST-run_1
"""

qrels = parse_trec_qrels(qrels_text)
run = parse_trec_run(run_text)
evaluation = evaluate_trec_run(run_text, qrels_text, cutoff=10)
comparison = compare_trec_runs(
    "q Q0 irrelevant 1 0.9 baseline\nq Q0 relevant 2 0.2 baseline\n",
    "q Q0 relevant 1 0.9 candidate\nq Q0 irrelevant 2 0.2 candidate\n",
    "q 0 relevant 1\nq 0 irrelevant 0\n",
    cutoff=1,
)
```

TREC qrels require four fields and signed ASCII integer relevance in
`[-127, 127]`. Runs require six fields, literal `Q0`, a positive rank, a
finite score, and one portable 1–20 character ASCII run tag. Blank and `#`
comment lines are ignored while physical error line numbers are preserved.
Evaluation orders runs by decreasing score, not the submitted rank field.

## Call RankWeave from a host

A host—including Naruon—should depend on the **published contract**, not on a
sibling source tree.

The published contract is:

1. **The installed Python package.** Import public names from `rankweave`.
   The package `__all__` list is the supported library surface. Pin an exact
   released version. A source-only API on this repository is not a published
   contract for a host while that host still pins an older package.
2. **The CLI JSON transports.** `rankweave compare`,
   `rankweave compare-family`, and `rankweave verify-artifacts` write
   independently versioned UTF-8 JSON documents. Default pairwise and family
   output remains the exact v1 field set. `--include-artifact-digests` is the
   only way to receive the corresponding v2 schema.
3. **The packaged report schemas.** Strict JSON Schema Draft 2020-12 resources
   describe every emitted pairwise and family v1/v2 document, plus the
   verification report. Discover them from the installed wheel; do not scrape
   this repository at runtime.

Naruon is expected to compose RankWeave through its hybrid-retrieval seam
(`services.hybrid_retrieval`) by depending on the published package. Other
hosts should do the same: add `rankweave` to their dependency set, call the
public API or CLI, and validate CLI output against the packaged schemas. Do
not vendor RankWeave files out of a Naruon checkout, and do not require
operators of this package to clone Naruon.

### Discover the installed report contracts

```bash
rankweave schema --report-type pairwise --schema-version v2
python -m rankweave schema --report-type family --schema-version v1
```

```python
from rankweave import available_report_schemas, load_report_schema

for descriptor in available_report_schemas():
    schema = load_report_schema(
        descriptor.report_type,
        descriptor.schema_version,
    )
    assert schema["properties"]["schema_version"]["const"] == (
        descriptor.transport_schema_id
    )
```

The runtime does not embed a validator. The host chooses a conforming Draft
2020-12 implementation. Structural validation does not authenticate a report,
verify external artifact bytes, or establish that a statistical conclusion is
scientifically valid.

See [Report JSON Schemas](docs/report-schemas.md) and
[RankWeave command-line interface](docs/cli.md).

### Compare a candidate family from a host process

```python
from rankweave import (
    CANDIDATE_GREATER_ALTERNATIVE,
    compare_trec_run_family,
)

report = compare_trec_run_family(
    "q Q0 irrelevant 1 0.9 baseline\nq Q0 relevant 2 0.2 baseline\n",
    {
        "model-a": (
            "q Q0 relevant 1 0.95 model-a\n"
            "q Q0 irrelevant 2 0.10 model-a\n"
        ),
        "model-b": (
            "q Q0 relevant 1 0.80 model-b\n"
            "q Q0 irrelevant 2 0.30 model-b\n"
        ),
    },
    "q 0 relevant 1\nq 0 irrelevant 0\n",
    cutoff=1,
    alternative=CANDIDATE_GREATER_ALTERNATIVE,
    familywise_alpha=0.05,
)

for candidate in report.candidates:
    print(
        candidate.candidate_id,
        candidate.comparison.significance.mean_difference,
        candidate.raw_p_value,
        candidate.holm_adjusted_p_value,
        candidate.rejected_at_familywise_alpha,
    )
```

The baseline and qrels are parsed and evaluated once. Every candidate is
tested with the same explicit metric, alternative, randomization count, and
seed. Holm correction controls false rejections within the supplied family; it
does not measure lift or justify automatic deployment.

## Select a fixed fusion policy

The caller defines the finite policy family before inspecting validation
results. Freeze the selected weights and evaluate them once on an independent
held-out test set before reporting final quality.

```python
from rankweave import tune_weighted_convex_fusion, tune_weighted_reciprocal_rank_fusion

convex = tune_weighted_convex_fusion(
    {
        "query-a": {
            "lexical": [("a", 1.0), ("b", 0.0)],
            "dense": [("b", 1.0), ("a", 0.0)],
        },
        "query-b": {
            "lexical": [("c", 0.9), ("d", 0.1)],
            "dense": [("d", 0.9), ("c", 0.1)],
        },
    },
    {"query-a": {"a": 3}, "query-b": {"c": 3}},
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=1,
)

rrf = tune_weighted_reciprocal_rank_fusion(
    {
        "query-a": {"lexical": ["a", "b"], "dense": ["b", "a"]},
        "query-b": {"lexical": ["c", "d"], "dense": ["d", "c"]},
    },
    {"query-a": {"a": 3}, "query-b": {"c": 3}},
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=10,
)
```

Caller-owned blocked folds and availability-time windows assess the selection
procedure without treating all-data final tuning as held-out quality:

- [Convex score-fusion policy tuning](docs/convex-fusion-tuning.md)
- [Explicit-fold convex fusion cross-validation](docs/convex-fusion-cross-validation.md)
- [Weighted-RRF explicit-fold cross-validation](docs/rrf-cross-validation.md)
- [Temporal convex-fusion backtesting](docs/temporal-convex-backtesting.md)

## Input and determinism guarantees

- numeric fusion, evaluation, and comparison inputs are finite;
- direct convex scores and weights obey their documented domains;
- RRF ranks, cutoffs, limits, and randomization counts are positive integers;
- item, query, and candidate identifiers are hashable and unique in scope;
- complete-list ties preserve first-seen order;
- comparisons align by query ID and use local seeded randomness only;
- family p-value ties are resolved by candidate input order;
- public result, evaluation, comparison, tuning, and TREC records are frozen;
- CLI artifact digests bind exact raw bytes and disclose no local path.

Both CLI comparison commands accept local files only and delegate parsing,
evaluation, randomization, and adjustment to the native Python APIs.

## Research and standards

Defaults, metrics, comparison, and interchange trace to the APA 7th edition
references in [`docs/research/`](docs/research/). Do not treat the short labels
below as a new bibliography.

- Bruch et al. (2024) — TM2C2 and theoretical normalization.
- Cormack et al. (2009) — reciprocal-rank fusion.
- Samuel et al. (2025) — weighted RRF under unequal channel reliability.
- Järvelin and Kekäläinen (2002) — graded cumulative gain.
- Smucker et al. (2007) — paired IR significance testing.
- Holm (1979) — sequentially rejective family-wise error control.
- NIST TREC and `trec_eval` — interchange and evaluation reference behavior.
- FIPS 180-4 — SHA-256 definition for exact artifact-byte evidence.
- SLSA v1.2 — provenance subject-digest and verification framing.
- RFC 8259 — interoperable UTF-8 JSON transport.
- Unicode UAX #15 — NFC normalization.

## Operator documentation

| Topic | Document |
|---|---|
| CLI transports, exits, and CI examples | [docs/cli.md](docs/cli.md) |
| Pairwise TREC comparison | [docs/trec-run-comparison.md](docs/trec-run-comparison.md) |
| Candidate-family comparison and Holm | [docs/trec-family-comparison.md](docs/trec-family-comparison.md) |
| TREC parse/format contracts | [docs/trec-interoperability.md](docs/trec-interoperability.md) |
| Report JSON Schemas | [docs/report-schemas.md](docs/report-schemas.md) |
| Artifact verification | [docs/artifact-verification.md](docs/artifact-verification.md) |
| Trusted publication | [docs/releasing.md](docs/releasing.md) |
| Architecture boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Contributor and automation procedure | [CONTRIBUTING.md](CONTRIBUTING.md) |

## License

Apache-2.0 — see [LICENSE](LICENSE).
