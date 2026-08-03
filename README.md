# rankweave

**Language-agnostic hybrid-retrieval fusion, evaluation, tuning, and strict
TREC interchange — pure Python and store-agnostic.**

RankWeave combines lexical, dense, learned-sparse, graph, and other retrieval
channels into deterministic rankings. It evaluates those rankings against
relevance judgments, selects fixed weighted-RRF policies on validation data,
and reads or writes standard TREC run and qrels artifacts. The runtime uses
only the Python standard library and has no dependency on a database,
embedding provider, search engine, or web framework.

RankWeave originated in the Context Search engine of
[naruon](https://github.com/ContextualWisdomLab/naruon) under Contextual Wisdom
Lab's ONE SOURCE MULTI USE convention: useful as a standalone package and as a
small reusable module inside a larger system.

## Why RankWeave

- **Research-grounded fusion.** The default convex strategy follows TM2C2;
  equal-weight and fixed-weight Reciprocal Rank Fusion are available for
  rank-only channels.
- **Production-shaped APIs.** Pass complete score-bearing or rank-only result
  lists instead of rebuilding per-item fusion inputs yourself.
- **Auditable decisions.** Immutable results preserve every channel's score,
  rank, weight, and contribution, including explicit missing evidence.
- **Closed experiment loop.** Built-in P@k, R@k, RR@k, and graded nDCG@k
  evaluation feeds deterministic weighted-RRF policy selection.
- **TREC interoperability.** Strict qrels and run parsing, canonical
  formatting, score-based ordering, and direct evaluation connect RankWeave to
  established information-retrieval benchmarks.
- **Fail-closed contracts.** Invalid numeric values, duplicate identifiers,
  mismatched query sets, malformed policies, and invalid interchange records
  raise stable `ValueError` exceptions rather than silently changing results.
- **Portable core.** Python 3.10+, typed, Apache-2.0, and no runtime
  dependencies.

## Install

Until PyPI Trusted Publishing is configured, install directly from GitHub:

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
    word_similarity_score=0.62,       # lexical score in [0, 1]
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

Missing or `None` scores contribute the theoretical minimum, zero. Weights
must be finite, non-negative, and sum to one.

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
records. An absent channel remains visible with `score=None` and a zero
contribution.

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
assert results[0].channel_ranks == (("lexical", 2), ("dense", 1))
```

Fixed-weight RRF for channels with different known reliability:

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

Every `FusedWeightedRankedItem` records each channel's rank, convex weight,
and reciprocal contribution. Missing evidence remains visible with
`rank=None` and contribution zero. Weights are fixed for one call; RankWeave
does not infer online query- or item-adaptive weights.

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
- precision uses the requested cutoff as its denominator, so short runs are
  penalized consistently;
- reciprocal rank is cutoff-bound;
- nDCG uses exponential gain (`2**relevance - 1`) and logarithmic discount;
- ranking and judgment mappings must contain exactly the same query IDs.
  Represent a no-result query with an empty sequence rather than omitting it.

The immutable report preserves per-query metrics and macro averages. This
nDCG variant is intentionally documented and is not claimed to be numerically
identical to `trec_eval`'s default identity-gain configuration.

## Tune a weighted-RRF policy

Provide complete channel rankings, held-out validation judgments, and named
candidate policies:

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
precision are also supported through exported objective constants. Every
candidate produces an immutable `WeightedRRFTuningTrial` containing its
weights, objective value, and complete `RankingEvaluationReport`. Exact ties
select the first candidate, preserving mapping insertion order.

This is validation-set model selection. Measure the chosen policy once more on
a separate held-out test set before making a production quality claim.

## Read and evaluate TREC artifacts

```python
from rankweave import evaluate_trec_run, parse_trec_qrels, parse_trec_run

qrels_text = """\
q1 0 document-a 2
q1 0 document-b 0
"""
run_text = """\
q1 Q0 document-a 1 0.93 rw1
q1 Q0 document-b 2 0.42 rw1
"""

qrels = parse_trec_qrels(qrels_text)
run = parse_trec_run(run_text)
report = evaluate_trec_run(run_text, qrels_text, cutoff=10)

assert run.rankings_by_query()["q1"][0] == "document-a"
assert qrels.relevance_by_query()["q1"]["document-a"] == 2.0
assert report.aggregate.mean_ndcg_at_k == 1.0
```

The TREC adapter enforces four-column qrels and six-column run records, literal
`Q0`, finite numeric fields, positive ranks, unique documents and submitted
ranks per query, one run tag, and a conservative 1–12 character
ASCII-alphanumeric run tag. Public dataclass construction is validated too;
callers cannot bypass parser contracts and then serialize malformed state.

Runs are evaluated in decreasing score order, matching TREC tool behavior
rather than trusting the submitted rank column. Exact score ties preserve input
order as a deterministic RankWeave extension. Negative qrels are retained in
the immutable audit artifact and omitted from evaluation as explicit unjudged
markers.

See [TREC interoperability](docs/trec-interoperability.md) for complete
contracts and compatibility notes.

## Hourly governed development loop

The repository includes an hourly workflow that performs:

`PR review/merge scan → review-feedback repair → exact-head revalidation → one
bounded buyer-visible product task when both queues are empty`.

PR governance is delegated to immutable, commit-pinned workflows in the
organization's central `.github` repository. Product development is
single-flight and uses GitHub's Copilot agent-tasks API only when a
user-to-server `COPILOT_GITHUB_TOKEN` is configured. Missing credentials,
unknown task states, task-list failures, or any open PR block new work.

See [Hourly commercialization loop](docs/operations/hourly-commercialization-loop.md)
for setup, permissions, failure modes, and verification.

## Input and ordering guarantees

- All numeric fusion and evaluation inputs must be finite.
- Direct convex scores and weights obey their documented domains.
- RRF ranks, eta, cutoffs, and limits must be positive integers; booleans and
  fractional values are rejected.
- Relevance grades must be finite and non-negative.
- Item identifiers must be hashable and unique within a channel or ranking.
- Complete-list APIs use deterministic first-seen ordering for exact score
  ties.
- TREC containers snapshot iterable inputs and reject inconsistent state.
- Public result, evaluation, tuning, and TREC records are frozen dataclasses.

## API overview

| Symbol | Purpose |
|---|---|
| `FusionSettings` | Immutable strategy and scalar fusion parameters. |
| `fuse_channel_scores(...)` | Fuse one lexical+dense candidate. |
| `weighted_convex_combination_score(...)` | N-channel scalar convex fusion. |
| `weighted_convex_fuse(...)` | Complete scored-list convex fusion with audit records. |
| `reciprocal_rank_fusion_score(...)` | Equal-weight scalar RRF. |
| `reciprocal_rank_fuse(...)` | Complete rank-list RRF with rank trails. |
| `weighted_reciprocal_rank_fusion_score(...)` | Fixed-weight scalar RRF. |
| `weighted_reciprocal_rank_fuse(...)` | Complete fixed-weight RRF with contribution trails. |
| `evaluate_ranking(...)` | P@k, R@k, RR@k, and graded nDCG@k for one ranking. |
| `evaluate_rankings(...)` | Per-query and macro evaluation for a query set. |
| `tune_weighted_reciprocal_rank_fusion(...)` | Select a fixed weighted-RRF policy on validation judgments. |
| `parse_trec_qrels(...)`, `parse_trec_run(...)` | Parse strict standard interchange text. |
| `format_trec_qrels(...)`, `format_trec_run(...)` | Emit canonical validated interchange text. |
| `evaluate_trec_run(...)` | Parse, score-order, and evaluate one run against qrels. |
| `normalize_search_text(...)` | NFC composition, whitespace collapse, and length cap. |

## Query-normalization contract

Character-trigram lexical retrieval is language-agnostic only when query and
indexed documents fold identically. `normalize_search_text` performs NFC
composition and whitespace shaping. Accent folding and lowercasing belong in
one store-side normalization function applied identically to indexed text and
bound queries.

## Research and standards

- **Bruch, Gai & Ingber (2023).** *An Analysis of Fusion Functions for
  Hybrid Retrieval.* ACM TOIS 42(1), arXiv:2210.11934 — TM2C2, theoretical
  normalization, multi-system extension, and sample-efficient tuning.
- **Cormack, Clarke & Büttcher (2009).** *Reciprocal Rank Fusion outperforms
  Condorcet and individual Rank Learning Methods.* SIGIR 2009 — RRF and the
  default `eta=60`.
- **Samuel et al. (2025).** *MMMORRF: Multimodal Multilingual Modularized
  Reciprocal Rank Fusion.* SIGIR 2025, DOI: 10.1145/3726302.3730157 —
  evidence for weighted RRF when channel reliability differs.
- **Järvelin & Kekäläinen (2002).** *Cumulated Gain-based Evaluation of IR
  Techniques.* ACM TOIS 20(4), DOI: 10.1145/582415.582418 — graded gain,
  rank discounting, and ideal-ranking normalization.
- **NIST TREC and `trec_eval`.** Four-column qrels, six-column submitted runs,
  score-order evaluation, and reference effectiveness conventions.
- **UAX #15.** Unicode NFC normalization.

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
