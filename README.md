# RankWeave

**Python-runtime-dependency-free, store-agnostic retrieval fusion, evaluation, statistical
comparison, tuning, TREC benchmarking, and auditable CLI workflows for Python
3.10+.**

RankWeave combines lexical, dense, learned-sparse, graph, and other retrieval
channels into deterministic rankings. It evaluates rankings, compares paired
systems, controls family-wise error across candidate experiments, tunes fixed
weighted-RRF policies, reads standard TREC artifacts, and exposes both pairwise
and candidate-family comparison contracts to shell and CI users. Python
adapters use only the standard library and the packaged Rust calculation core.

RankWeave originated in the Context Search engine of
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon) and
remains suitable both as a standalone package and as a small MSA module.

## Why RankWeave

- **Research-grounded fusion:** TM2C2 convex fusion and reciprocal-rank fusion,
  including fixed channel-reliability weights.
- **Production-shaped APIs:** fuse complete scored or rank-only result lists.
- **Auditable decisions:** frozen records preserve every score, rank, weight,
  contribution, query metric, p-value, and benchmark artifact.
- **Closed experiment loop:** evaluate, compare, correct multiple comparisons,
  and tune policies without a numerical runtime dependency.
- **Strict TREC workflow:** parse, format, evaluate, compare two runs, or compare
  a named family of candidates against one baseline.
- **Shell-ready evidence:** `rankweave compare` and `rankweave compare-family`
  emit versioned JSON audit reports without requiring Python glue.
- **Exact artifact binding:** opt-in v2 reports retain SHA-256 and raw byte counts
  for every run and qrels input without exposing local paths.
- **Fail-closed contracts:** malformed values, duplicate identifiers, missing
  queries, and invalid artifacts raise stable validation errors.
- **Portable core:** Apache-2.0, typed, Python 3.10+, and one packaged Rust
  calculation core with no third-party Python runtime dependency.

## Installation

Until PyPI Trusted Publishing is configured:

```bash
pip install "rankweave @ git+https://github.com/ContextualWisdomLab/RankWeave.git"
```

For development:

```bash
git clone https://github.com/ContextualWisdomLab/RankWeave.git
cd RankWeave
pip install -e ".[dev]"
```

The wheel installs both the Python package and the `rankweave` console command.

## Fuse retrieval channels

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

Fuse arbitrary normalized channels:

```python
from rankweave import weighted_convex_combination_score

score = weighted_convex_combination_score(
    {"semantic": 0.80, "lexical": 0.55, "sparse": 0.65},
    {"semantic": 0.50, "lexical": 0.30, "sparse": 0.20},
)
```

Fuse complete score lists:

```python
from rankweave import weighted_convex_fuse

results = weighted_convex_fuse(
    {
        "semantic": [("document-b", 0.90), ("document-a", 0.50)],
        "lexical": [("document-a", 0.80), ("document-c", 0.70)],
    },
    {"semantic": 0.60, "lexical": 0.40},
    limit=10,
)

assert results[0].item_id == "document-a"
```

Fuse complete rank-only lists:

```python
from rankweave import weighted_reciprocal_rank_fuse

results = weighted_reciprocal_rank_fuse(
    {
        "lexical": ["document-a", "document-b"],
        "dense": ["document-b", "document-c"],
    },
    {"lexical": 0.25, "dense": 0.75},
    limit=10,
)
```

Complete-list results expose immutable per-channel contribution evidence,
including explicit missing channels.

## Rank provider-produced semantic units

RankWeave compares vectors that your authorized retrieval boundary already
obtained. It does not select or call an embedding model.

```python
from rankweave import SemanticUnitCandidate, rank_semantic_units

report = rank_semantic_units(
    [1.0, 0.0],
    [
        SemanticUnitCandidate("post-a", "paragraph-1", [1.0, 0.0]),
        SemanticUnitCandidate("post-a", "paragraph-2", [0.0, 1.0]),
        SemanticUnitCandidate("post-b", "paragraph-1", [0.8, 0.2]),
    ],
)

assert report.results[0].item_id == "post-a"
assert report.results[0].winning_unit_id == "paragraph-1"
```

The report binds the ordered input with SHA-256, identifies the schema and
algorithm versions, and retains the winning semantic unit for each item. Invalid
dimensions, non-finite values, zero vectors, and duplicate item/unit pairs fail
with stable error codes. See [ADR 0007](docs/adr/0007-semantic-unit-cosine-ranking.md).

For repeated queries over one governed snapshot, `SemanticUnitExactIndex`
validates canonical packed vectors once, records model/dimension/vector and
snapshot digests, and scores only caller-supplied authorized candidate IDs on
the deterministic multithreaded Rust CPU path. Snapshot replacement is atomic;
v1 exposes no partial mutation or approximate retrieval. The caller still owns
persistence, model selection, ABAC, and result post-authorization. See
[ADR 0008](docs/adr/0008-persistent-exact-semantic-index.md).

## Evaluate ranking quality

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

The evaluation API reports precision@k, recall@k, reciprocal-rank@k, and graded
nDCG@k. Ranking and judgment mappings must contain exactly the same query IDs.
The nDCG implementation uses gain `2**relevance - 1`; it is not claimed to be
numerically identical to `trec_eval`'s default identity-gain configuration.

## Compare a candidate with a baseline

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

`compare_ranking_reports` compares existing immutable evaluation reports.
`compare_rankings` evaluates and compares two ranking mappings. Candidate values
are aligned by query ID, never tuple position.

For up to 16 non-zero query differences, RankWeave enumerates all sign
assignments exactly. Larger comparisons use deterministic local Monte Carlo
randomization with a plus-one p-value correction. Supported metrics are
precision, recall, reciprocal rank, and nDCG; supported alternatives are
`two-sided`, `candidate-greater`, and `candidate-less`.

A p-value is not an effect-size or business-value threshold. Report the observed
mean difference and per-query evidence with the p-value.

## Cross-validate convex score-fusion selection

```python
from rankweave import cross_validate_weighted_convex_fusion

report = cross_validate_weighted_convex_fusion(
    scored_results_by_query,
    relevance_by_query,
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    {
        "query-a1": "source-family-a",
        "query-a2": "source-family-a",
        "query-b1": "source-family-b",
        "query-b2": "source-family-b",
    },
    cutoff=10,
)

print(report.out_of_fold_evaluation.aggregate.mean_ndcg_at_k)
print(report.final_tuning.best_policy_id)
```

Every held-out fold is evaluated with a policy selected only from the remaining
queries. Fold IDs are caller-owned so translations, paraphrases, revisions,
tenants, projects, events, or time blocks can remain together when the
experimental boundary requires it. The out-of-fold evaluation estimates the
selection procedure under that exact fold design; the separate full-data tuning
report recommends one future policy and is not held-out evidence.

See [Explicit-fold convex fusion cross-validation](docs/convex-fusion-cross-validation.md).

## Tune a fixed convex score-fusion policy

```python
from rankweave import tune_weighted_convex_fusion

report = tune_weighted_convex_fusion(
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
    {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    },
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=1,
)

assert report.best_policy_id == "lexical-heavy"
```

The caller defines the finite policy family before inspecting validation
results. Every trial retains its complete immutable evaluation, and the first
policy wins an exact objective tie. Freeze the selected weights and evaluate
them once on an independent held-out test set before reporting final quality.

See [Convex score-fusion policy tuning](docs/convex-fusion-tuning.md).

## Tune a fixed weighted-RRF policy

```python
from rankweave import tune_weighted_reciprocal_rank_fusion

report = tune_weighted_reciprocal_rank_fusion(
    {
        "query-a": {
            "lexical": ["a", "b"],
            "dense": ["b", "a"],
        },
        "query-b": {
            "lexical": ["c", "d"],
            "dense": ["d", "c"],
        },
    },
    {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    },
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=10,
)

assert report.best_policy_id == "lexical-heavy"
```

Tuning is validation-set model selection. Evaluate the selected policy once on
an independent held-out test set before reporting final quality.

## Parse and evaluate TREC artifacts

```python
from rankweave import evaluate_trec_run, parse_trec_qrels, parse_trec_run

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
report = evaluate_trec_run(run_text, qrels_text, cutoff=10)
```

TREC qrels require four fields and signed ASCII integer relevance in
`[-127, 127]`. Runs require six fields, literal `Q0`, a positive rank, finite
score, and one portable 1–20 character ASCII run tag containing only ASCII
letters, digits, periods, underscores, or hyphens. Blank and `#` comment lines
are ignored while physical error line numbers are preserved. Evaluation orders
runs by decreasing score, not the submitted rank field.

## Compare two TREC runs directly

```python
from rankweave import compare_trec_runs

report = compare_trec_runs(
    "q Q0 irrelevant 1 0.9 baseline\nq Q0 relevant 2 0.2 baseline\n",
    "q Q0 relevant 1 0.9 candidate\nq Q0 irrelevant 2 0.2 candidate\n",
    "q 0 relevant 1\nq 0 irrelevant 0\n",
    cutoff=1,
)
```

`TrecRunComparisonReport` retains both parsed runs, qrels, both evaluations, and
the complete paired statistical result. Identical run tags are allowed because
tags are provenance rather than artifact identity.

See [Direct TREC run comparison](docs/trec-run-comparison.md).

## Run a pairwise comparison from shell or CI

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --alternative candidate-greater \
  --pretty > comparison.json
```

The equivalent module invocation is `python -m rankweave compare ...`.
Default execution emits `rankweave.trec-comparison.v1` JSON. Expected usage,
filesystem, UTF-8, size, TREC, evaluation, and statistical validation failures
emit no JSON, write one `rankweave: error: ...` line to stderr, and return `2`.

## Compare a TREC candidate family with Holm correction

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

The baseline and qrels are parsed and evaluated once. Every candidate is tested
with the same explicit metric, alternative, randomization count, and seed.
RankWeave applies Holm's step-down correction to the resulting family of raw
p-values and returns both raw and adjusted evidence in candidate input order.

The candidate family must be defined before inspecting results. Holm correction
controls false rejections within the supplied family; it does not measure lift
or justify automatic deployment.

See [TREC candidate-family comparison](docs/trec-family-comparison.md).

## Run the candidate family from shell or CI

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

Repeatable `--candidate ID=PATH` options define the complete family and preserve
command-line order. Default execution emits
`rankweave.trec-family-comparison.v1` JSON with each candidate's effect, raw and
Holm-adjusted p-values, family-wise decision, run provenance, and complete
per-query differences.

## Bind reports to exact input bytes

Run tags are descriptive provenance and may repeat. Add
`--include-artifact-digests` when a persisted report must identify the exact
baseline, candidate, and qrels bytes that were evaluated:

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
  --candidate model-a=model-a.run \
  --candidate model-b=model-b.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests > family-comparison.json
```

Digest mode uses the opt-in schemas `rankweave.trec-comparison.v2` and
`rankweave.trec-family-comparison.v2`. Each artifact record contains a SHA-256
hex digest and exact raw `byte_count`; candidate evidence retains the declared
family order. Local paths are never emitted.

Hashes cover the original bounded bytes before UTF-8 decoding. Comments, line
endings, and trailing whitespace therefore change artifact identity even when
they do not change the evaluated ranking. SHA-256 evidence is an integrity
binding, not a signature, producer-authentication mechanism, trusted-execution
proof, or SLSA-level claim.

See [RankWeave command-line interface](docs/cli.md) for v1/v2 field order,
verification examples, and operator boundaries.

## Discover machine-readable report contracts

RankWeave 0.13.0 ships strict JSON Schema Draft 2020-12 resources for every
pairwise and candidate-family v1/v2 transport. Shell and container consumers
can retrieve the exact installed contract without locating package files:

```bash
rankweave schema --report-type pairwise --schema-version v2
```

The equivalent module entrypoint is:

```bash
python -m rankweave schema --report-type family --schema-version v1
```

Python and MSA consumers can use the dependency-free resource API:

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

The runtime does not embed a validator. Consumers select a conforming Draft
2020-12 implementation appropriate to their platform. Structural validation
does not authenticate a report, verify external artifact bytes, or establish
that a statistical conclusion is scientifically valid. See
[Report JSON Schemas](docs/report-schemas.md).

## Cross-validate fixed weighted-RRF policies

Rank-only retrieval systems can evaluate their complete fixed-weight selection
procedure with explicit blocked folds:

```python
from rankweave import cross_validate_weighted_reciprocal_rank_fusion

report = cross_validate_weighted_reciprocal_rank_fusion(
    channel_rankings_by_query,
    relevance_by_query,
    candidate_channel_weights,
    fold_id_by_query,
    cutoff=10,
    rank_constant_eta=60,
)
```

Every fold tunes weights only on complementary training queries, applies the
selected weights and one fixed eta unchanged to held-out rank lists, and retains
the complete tuning and evaluation reports. The aggregate out-of-fold result is
kept separate from all-data final tuning. The caller owns leakage-safe grouping
for translations, users, tenants, revisions, projects, events, and time blocks.

See [Weighted-RRF explicit-fold cross-validation](docs/rrf-cross-validation.md).

## Backtest convex policies by availability time

Use `backtest_weighted_convex_fusion` when a policy must be selected only from
information available before each historical assessment window. The caller
supplies timezone-aware availability timestamps and explicit ordered windows;
RankWeave rejects future-evidence leakage, overlapping held-out windows,
incomplete query accounting, and ambiguous same-instant boundaries.

Each window preserves the complete training tuning report, selected fixed
weights, held-out rankings, and held-out evaluation. The report also reconstructs
one original-order out-of-sample evaluation and keeps the all-data final policy
recommendation separate from prospective evidence.

See [Temporal convex-fusion backtesting](docs/temporal-convex-backtesting.md).

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

Both CLI workflows accept local files only and delegate all parsing,
evaluation, randomization, and adjustment behavior to the native Python APIs.
Inputs default to a 64 MiB limit **per artifact**. The same bounded payload is
hashed, counted, and strictly decoded once, so a file that grows after its
initial size check cannot trigger an unbounded in-memory read.

## Hourly governed development loop

The default branch runs an hourly workflow at minute 17:

`PR review/merge scan → review-feedback repair → exact-head revalidation → one
bounded buyer-visible product proposal when the governed PR queue is empty`.

PR inspection, review repair, and merge decisions use immutable reusable
workflows from the organization's central `.github` repository. The local
product stage uses a hash-pinned OpenCode binary with the official NVIDIA
provider and `NVIDIA_NIM_API_KEY`; it does not use GitHub Copilot Agent Tasks or
alter the existing review-agent credential path.

The workflow first permits edits only to tests and a design specification, then
runs pytest without network or inherited credentials and requires a genuine
failed test. Only then may the agent implement one bounded production change.
`AGENTS.md`, workflow, ownership, security, environment, and repository-control
files remain maintainer-owned and outside autonomous scope. Ruff, the complete
tests, 100% line/branch coverage, wheel build, offline installation, import
smoke, and `pip check` run in a network-isolated process.

Before requesting the short-lived OIDC-derived GitHub App token, the workflow
rechecks both the open-PR queue and exact `main` SHA. It repeats both checks
immediately before opening one PR. Generated work is never self-approved,
merged, published, or released.

See [Hourly commercialization loop](docs/operations/hourly-commercialization-loop.md)
for the credential, sandbox, failure, and operating contracts.

## Research and standards

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

Full APA 7th edition references are in [`docs/research/`](docs/research/).

## Development

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report    # 100% line + branch coverage required
python -m pip wheel . --no-deps --wheel-dir dist
```

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Verify persisted artifact evidence

RankWeave 0.18.0 can compare explicit local files with the unsigned SHA-256 and raw byte-count evidence in a persisted v2 report without exposing file paths or payloads:

```bash
rankweave verify-artifacts \
  --report comparison.json \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt
```

Candidate-family verification uses ordered, repeatable `--candidate ID=PATH` arguments. Exit status `0` means all bytes match, `1` means at least one artifact differs, and `2` means the command or evidence is invalid. A match is an integrity comparison only—not authentication, signature verification, provenance verification, or a SLSA claim.

## Trusted distribution and provenance

RankWeave releases are built from the exact published GitHub Release tag, tested at 100% production statement and branch coverage, transferred between jobs as one immutable distribution artifact, and published through PyPI Trusted Publishing after the protected `pypi` environment approves the deployment.

After a version has been published and independently verified, install it from PyPI:

```bash
python -m pip install rankweave==0.18.0
```

Before the first Trusted Publisher is configured or when a version has not been published, use a reviewed source checkout instead of assuming that the PyPI name is owned by this project. See [`docs/releasing.md`](docs/releasing.md) for the exact publisher identity, release procedure, and GitHub/PyPI attestation verification boundaries.
