# RankWeave

**Dependency-free, store-agnostic retrieval fusion, evaluation, statistical
comparison, tuning, and strict TREC interchange for Python 3.10+.**

RankWeave combines lexical, dense, learned-sparse, graph, and other retrieval
channels into deterministic rankings. It evaluates those rankings against
relevance judgments, compares paired systems with transparent randomization,
and can select a fixed weighted-RRF policy on a validation set. The runtime
uses only the Python standard library.

RankWeave originated in the Context Search engine of
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
and remains suitable both as a standalone package and as a small MSA module.

## Why RankWeave

- **Research-grounded fusion:** TM2C2 convex score fusion and reciprocal-rank
  fusion, including fixed channel-reliability weights.
- **Production-shaped APIs:** fuse complete scored or rank-only result lists,
  not only one candidate at a time.
- **Auditable decisions:** immutable records preserve each channel's score,
  rank, weight, and contribution, including missing evidence.
- **Closed experiment loop:** P@k, R@k, RR@k, graded nDCG@k, paired
  randomization, and deterministic validation-set policy selection.
- **TREC interoperability:** strict qrels/run parsing, canonical formatting,
  score-ordered rankings, comment handling, and direct evaluation.
- **Fail-closed contracts:** malformed numeric values, duplicate identifiers,
  incomplete query sets, and invalid interchange records raise `ValueError`
  instead of silently changing results.
- **Portable core:** typed, Apache-2.0, Python 3.10+, and no runtime dependency.

## Installation

Until PyPI Trusted Publishing is enabled, install from GitHub:

```bash
pip install "rankweave @ git+https://github.com/ContextualWisdomLab/RankWeave.git"
```

For development:

```bash
git clone https://github.com/ContextualWisdomLab/RankWeave.git
cd RankWeave
pip install -e ".[dev]"
```

## Fuse one candidate

```python
from rankweave import FusionSettings, fuse_channel_scores

score = fuse_channel_scores(
    word_similarity_score=0.62,       # lexical similarity in [0, 1]
    cosine_distance=0.30,             # dense distance in [0, 2]
    channel_ranks={"lexical": 1, "dense": 1},
    settings=FusionSettings(),        # TM2C2, semantic alpha = 0.7
)
```

For arbitrary normalized channels:

```python
from rankweave import weighted_convex_combination_score

score = weighted_convex_combination_score(
    {"semantic": 0.80, "lexical": 0.55, "sparse": 0.65},
    {"semantic": 0.50, "lexical": 0.30, "sparse": 0.20},
)
```

Weights must be finite, non-negative, and sum to one. Missing or `None` scores
contribute the theoretical minimum, zero.

## Fuse complete scored lists

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

best = results[0]
assert best.item_id == "document-a"
assert round(best.score, 2) == 0.62
```

Each `FusedScoredItem` contains immutable `WeightedChannelContribution`
records. An absent channel remains visible with `score=None` and contribution
zero.

## Fuse complete rank-only lists

Equal-weight RRF:

```python
from rankweave import reciprocal_rank_fuse

results = reciprocal_rank_fuse(
    {
        "lexical": ["document-a", "document-b"],
        "dense": ["document-b", "document-c"],
    },
    limit=10,
)

assert results[0].item_id == "document-b"
```

Fixed-weight RRF:

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

best = results[0]
assert best.item_id == "document-b"
assert best.channel_contributions[0].rank == 2
assert best.channel_contributions[1].rank == 1
```

Every weighted-RRF result records each channel's rank, convex weight, and
reciprocal contribution. Missing evidence remains visible with `rank=None`.

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
print(report.query_metrics[0].metrics.reciprocal_rank_at_k)
```

Evaluation contracts are explicit:

- positive grades count as relevant for precision, recall, and reciprocal rank;
- unjudged items receive grade zero;
- precision uses the requested cutoff as its denominator;
- reciprocal rank is cutoff-bound;
- nDCG uses gain `2**relevance - 1` and logarithmic discount;
- ranking and judgment mappings must contain exactly the same query IDs.

The nDCG variant is documented and is not claimed to be numerically identical
to `trec_eval`'s default identity-gain configuration.

## Compare a candidate system with a baseline

```python
from rankweave import (
    CANDIDATE_GREATER_ALTERNATIVE,
    compare_rankings,
)

comparison = compare_rankings(
    {
        "query-a": ["irrelevant", "relevant-a"],
        "query-b": ["irrelevant", "relevant-b"],
    },
    {
        "query-a": ["relevant-a", "irrelevant"],
        "query-b": ["relevant-b", "irrelevant"],
    },
    {
        "query-a": {"relevant-a": 1},
        "query-b": {"relevant-b": 1},
    },
    cutoff=1,
    metric_name="ndcg_at_k",
    alternative=CANDIDATE_GREATER_ALTERNATIVE,
)

print(comparison.significance.mean_difference)
print(comparison.significance.p_value)
```

`compare_rankings` evaluates both systems on one complete judged query set,
then applies a paired Fisher sign-randomization test to candidate-minus-baseline
metric differences. `compare_ranking_reports` performs the same comparison on
existing immutable evaluation reports.

Supported metrics are precision@k, recall@k, reciprocal-rank@k, and nDCG@k.
Supported alternatives are `two-sided`, `candidate-greater`, and
`candidate-less`.

The comparison contract is intentionally strict:

- both systems must use the same positive cutoff and exactly the same query IDs;
- candidate metrics are joined to baseline metrics by query ID, never position;
- every selected per-query value must be finite and within `[0, 1]`;
- duplicate or unhashable query IDs are rejected;
- all aligned values and differences are preserved in immutable records.

Up to 16 non-zero query differences are enumerated exactly. Larger comparisons
use a local deterministic PRNG, default seed `0`, 10,000 sign assignments, and
the plus-one Monte Carlo correction, so a finite simulation never reports a
zero p-value. The global Python random state is not touched.

A p-value is evidence about sampling uncertainty under the paired null; it is
not an effect-size threshold, business-value estimate, or substitute for an
independent held-out test set. Report the mean difference and per-query audit
trail alongside the p-value.

## Tune a weighted-RRF policy

```python
from rankweave import tune_weighted_reciprocal_rank_fusion

report = tune_weighted_reciprocal_rank_fusion(
    {
        "query-a": {
            "lexical": ["document-a", "document-b"],
            "dense": ["document-b", "document-a"],
        },
        "query-b": {
            "lexical": ["document-c", "document-d"],
            "dense": ["document-d", "document-c"],
        },
    },
    {
        "query-a": {"document-a": 3},
        "query-b": {"document-c": 3},
    },
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=10,
)

assert report.best_policy_id == "lexical-heavy"
```

The default objective is macro nDCG@k. Macro reciprocal rank, recall, and
precision are also supported. Exact ties select the first candidate in mapping
insertion order. This is validation-set model selection: evaluate the selected
policy once more on an independent held-out test set before reporting final
quality.

## Read, write, and evaluate TREC artifacts

```python
from rankweave import (
    evaluate_trec_run,
    format_trec_qrels,
    parse_trec_qrels,
    parse_trec_run,
)

qrels_text = """\
# topic judgments
q1 0 document-a 2
q1 0 document-b 0
"""
run_text = """\
# submitted run
q1 Q0 document-a 1 0.93 NIST-run_1
q1 Q0 document-b 2 0.42 NIST-run_1
"""

qrels = parse_trec_qrels(qrels_text)
run = parse_trec_run(run_text)
report = evaluate_trec_run(run_text, qrels_text, cutoff=10)

assert run.rankings_by_query()["q1"][0] == "document-a"
assert qrels.relevance_by_query()["q1"]["document-a"] == 2
assert format_trec_qrels(qrels).startswith("q1 0 document-a 2")
assert report.aggregate.mean_ndcg_at_k == 1.0
```

### TREC contracts

- qrels content records have exactly four fields;
- qrels relevance is a signed ASCII-decimal integer in `[-127, 127]`;
- run content records have exactly six fields and literal `Q0`;
- run ranks are positive ASCII-decimal integers;
- run scores are finite real numbers;
- one document and one submitted rank are allowed per query;
- a run uses one tag consisting of 1–20 ASCII letters, digits, periods,
  underscores, or hyphens;
- blank lines and `#` comment lines are ignored while physical diagnostic line
  numbers are preserved.

Runs are evaluated in decreasing score order rather than trusting the submitted
rank column. Exact score ties preserve source order as RankWeave's documented
deterministic extension. Negative qrels remain in the immutable audit artifact
and are omitted from evaluation as explicit unjudged markers.

See [TREC interoperability](docs/trec-interoperability.md) for the full contract
and deliberate differences from permissive reference-tool behavior.

## Input and ordering guarantees

- all numeric fusion, evaluation, and comparison inputs must be finite;
- direct convex scores and weights obey their documented domains;
- RRF ranks, eta, cutoffs, limits, and randomization counts are positive
  integers, not booleans;
- relevance grades used by the generic evaluation API are non-negative;
- item and query identifiers are hashable and unique in their scope;
- complete-list APIs use deterministic first-seen ordering for exact ties;
- comparison aligns queries by identifier and uses only local seeded randomness;
- public result, evaluation, comparison, tuning, and TREC records are frozen
  dataclasses.

## Hourly governed development loop

The default branch contains a scheduled workflow at minute 17 of every hour:

`PR review/merge scan → review-feedback repair → exact-head revalidation → one
bounded buyer-visible product task when both queues are empty`.

PR governance uses immutable, commit-pinned reusable workflows from the
organization's central `.github` repository. New Copilot agent tasks require a
user-to-server secret named `COPILOT_GITHUB_TOKEN` with repository-scoped Agent
Tasks read/write permission. Missing credentials, unknown task states,
task-list failures, failed governance jobs, or any open PR block new work.

See [Hourly commercialization loop](docs/operations/hourly-commercialization-loop.md)
for setup, permissions, and failure modes.

## API overview

| Symbol | Purpose |
|---|---|
| `FusionSettings` | Immutable strategy and scalar fusion parameters. |
| `fuse_channel_scores(...)` | Fuse one lexical+dense candidate. |
| `weighted_convex_combination_score(...)` | N-channel scalar convex fusion. |
| `weighted_convex_fuse(...)` | Complete scored-list fusion with audit records. |
| `reciprocal_rank_fusion_score(...)` | Equal-weight scalar RRF. |
| `reciprocal_rank_fuse(...)` | Complete rank-list RRF. |
| `weighted_reciprocal_rank_fusion_score(...)` | Fixed-weight scalar RRF. |
| `weighted_reciprocal_rank_fuse(...)` | Complete fixed-weight RRF. |
| `evaluate_ranking(...)` | P@k, R@k, RR@k, and graded nDCG@k. |
| `evaluate_rankings(...)` | Per-query and macro evaluation. |
| `compare_ranking_reports(...)` | Paired randomization of two evaluation reports. |
| `compare_rankings(...)` | Evaluate and compare two complete ranking maps. |
| `tune_weighted_reciprocal_rank_fusion(...)` | Select a validation policy. |
| `parse_trec_qrels(...)`, `parse_trec_run(...)` | Parse strict TREC text. |
| `format_trec_qrels(...)`, `format_trec_run(...)` | Emit canonical text. |
| `evaluate_trec_run(...)` | Evaluate one score-ordered run against qrels. |
| `normalize_search_text(...)` | NFC composition, whitespace collapse, and cap. |

## Research and standards

- Bruch, Gai & Ingber (2023), *An Analysis of Fusion Functions for Hybrid
  Retrieval* — TM2C2 and theoretical normalization.
- Cormack, Clarke & Büttcher (2009), *Reciprocal Rank Fusion outperforms
  Condorcet and individual Rank Learning Methods* — RRF and `eta=60`.
- Samuel et al. (2025), *MMMORRF* — weighted RRF when channel reliability
  differs.
- Järvelin & Kekäläinen (2002), *Cumulated Gain-based Evaluation of IR
  Techniques* — graded gain and ideal-ranking normalization.
- Smucker, Allan & Carterette (2007), *A Comparison of Statistical
  Significance Tests for Information Retrieval Evaluation* — paired
  randomization as a suitable IR system-comparison method.
- NIST TREC and `trec_eval` — interchange and evaluation reference behavior.
- Unicode UAX #15 — NFC normalization.

Detailed citations and redistribution notes are in
[`docs/research/`](docs/research/).

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
