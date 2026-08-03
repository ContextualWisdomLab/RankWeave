# rankweave

**Language-agnostic hybrid-retrieval fusion and evaluation — pure-Python,
store-agnostic.**

`rankweave` decides *how to combine* scores from lexical, dense,
learned-sparse, and other retrieval channels into one ranking, then measures
how well that ranking performs against relevance judgments. It ships
research-grounded convex score fusion for two or more normalized channels,
complete-list score and rank fusion with audit trails, immutable retrieval
evaluation reports, and the query-side Unicode normalization that makes
character-level lexical matching language-agnostic. It has **no dependencies**
(stdlib only) and **no opinion about your store** — bring your own channels;
rankweave combines and evaluates their evidence.

It is extracted from the Context Search engine of
[naruon](https://github.com/ContextualWisdomLab/naruon), following the
lab's ONE SOURCE MULTI USE convention: standalone product *and*
submodule-importable.

## Why

A convex combination of **theoretically** min-max normalized scores
(TM2C2) beats Reciprocal Rank Fusion in- and out-of-domain, is robust
for `alpha ∈ [0.6, 0.8]` with no training data, and — unlike rank
fusion — preserves the score distribution (Bruch, Gai & Ingber 2023).
Their two-system analysis also extends directly to multiple retrieval
systems. RRF remains available for channels that expose only ranks, with
an optional fixed convex weighting policy when channels have different
reliability. Built-in evaluation closes the loop from choosing a fusion
policy to validating it on held-out judgments. See
[`docs/research/`](docs/research/) for the grounding.

## Install

Until PyPI publishing is enabled, install RankWeave directly from the
repository:

```bash
pip install "rankweave @ git+https://github.com/ContextualWisdomLab/RankWeave.git"
```

For an editable development checkout:

```bash
git clone https://github.com/ContextualWisdomLab/RankWeave.git
cd RankWeave
pip install -e ".[dev]"
```

## Quickstart

```python
from rankweave import FusionSettings, fuse_channel_scores, normalize_search_text

# 1) Normalize the query the same way you normalize indexed documents
#    (NFC compose; do accent-folding + lowercasing on the store side too).
query = normalize_search_text("  Trần Hưng Đạo 회의  ")   # -> "Trần Hưng Đạo 회의"

# 2) Run your own lexical + dense channels, then fuse per candidate.
settings = FusionSettings()                 # TM2C2, semantic weight alpha = 0.7
score = fuse_channel_scores(
    word_similarity_score=0.62,             # lexical channel score in [0, 1]
    cosine_distance=0.30,                   # dense channel distance in [0, 2]
    channel_ranks={"lexical": 1, "dense": 1},
    settings=settings,
)                                            # -> bounded [0, 1] fused score
```

A channel that did not return a candidate contributes its theoretical
minimum (absent evidence is the infimum, not an imputed value). Pass
`FusionSettings(strategy_name="reciprocal_rank_fusion")` to fuse by rank
instead — then only `channel_ranks` matters.

For three or more score-producing channels, normalize each score to `[0, 1]`
and supply explicit convex weights:

```python
from rankweave import weighted_convex_combination_score

multi_channel_score = weighted_convex_combination_score(
    {"semantic": 0.80, "lexical": 0.55, "sparse": 0.65},
    {"semantic": 0.50, "lexical": 0.30, "sparse": 0.20},
)
```

Use `theoretical_min_max_normalize` for bounded scoring functions before
calling the multi-channel helper. Missing or `None` channel scores contribute
zero; weights must be non-negative and sum to one.

To fuse complete normalized-score result lists, pass each channel's
`(item_id, score)` pairs together with the shared convex weights:

```python
from rankweave import weighted_convex_fuse

fused_results = weighted_convex_fuse(
    {
        "semantic": [("document-b", 0.90), ("document-a", 0.50)],
        "lexical": [("document-a", 0.80), ("document-c", 0.70)],
    },
    {"semantic": 0.60, "lexical": 0.40},
    limit=10,
)

best_result = fused_results[0]
assert best_result.item_id == "document-a"
assert round(best_result.score, 2) == 0.62
```

Every result includes immutable per-channel contribution records containing
the normalized score, configured weight, and resulting weighted contribution.
Channels that did not return an item remain visible with `score=None` and a
zero contribution, making production ranking decisions directly auditable.

To fuse complete rank-only result lists, pass item identifiers in rank order:

```python
from rankweave import reciprocal_rank_fuse

fused_results = reciprocal_rank_fuse(
    {
        "lexical": ["document-a", "document-b"],
        "dense": ["document-b", "document-c"],
    },
    limit=10,
)

best_result = fused_results[0]
assert best_result.item_id == "document-b"
assert best_result.channel_ranks == (("lexical", 2), ("dense", 1))
```

When rank-only channels have different known reliability, supply one fixed
convex weighting policy for the call:

```python
from rankweave import weighted_reciprocal_rank_fuse

weighted_results = weighted_reciprocal_rank_fuse(
    {
        "lexical": ["document-a", "document-b"],
        "dense": ["document-b", "document-c"],
    },
    {"lexical": 0.25, "dense": 0.75},
    limit=10,
)

best_weighted_result = weighted_results[0]
assert best_weighted_result.item_id == "document-b"
assert best_weighted_result.channel_contributions[0].rank == 2
assert best_weighted_result.channel_contributions[1].rank == 1
```

The weighted RRF result records every channel's rank, weight, and reciprocal
contribution. Missing evidence remains visible with `rank=None` and a zero
contribution. Weights are fixed per call; RankWeave does not infer adaptive
weights from the query or item. Equal positive weights preserve ordinary RRF
ordering, although the numeric scores differ by a common scaling factor.

Complete-list fusion rejects duplicate item identifiers within a channel and
uses deterministic first-seen input order when scores tie. RRF results retain
the full per-channel rank trail used to calculate each fused score.

## Evaluate ranking quality

Evaluate one ranking or a complete query set without introducing a metrics
framework dependency:

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

`evaluate_ranking` and `evaluate_rankings` report precision@k, recall@k,
reciprocal-rank@k, and graded nDCG@k. Their contracts are explicit:

- positive grades count as relevant for precision, recall, and reciprocal rank;
- unjudged items receive relevance grade zero;
- precision uses the requested cutoff as its denominator, so short result
  lists are penalized rather than silently receiving an easier denominator;
- reciprocal rank is bounded by the requested cutoff;
- nDCG uses exponential gain (`2**relevance - 1`) and logarithmic discount;
- aggregate evaluation requires exactly matching ranking and judgment query
  IDs. Represent a no-result query with an empty sequence rather than omitting
  it, preventing dropped queries from inflating reported quality.

Every report is immutable and preserves per-query metrics alongside macro
averages, making offline experiments and release gates reproducible. The nDCG
variant is intentionally documented and is not claimed to be numerically
identical to `trec_eval`'s default identity-gain configuration.

All numeric fusion and evaluation inputs must be finite. `NaN` and positive or
negative infinity raise `ValueError` rather than being clamped or propagated.
Direct convex helpers require scores and alpha in `[0, 1]`; RRF ranks and eta
must be positive integers, not booleans or fractions. Relevance grades must be
finite and non-negative.

## API

| Symbol | Purpose |
|---|---|
| `FusionSettings` | Immutable strategy + parameters (`strategy_name`, `semantic_weight_alpha`, `rank_constant_eta`). |
| `fuse_channel_scores(...)` | Fuse the common lexical-word-similarity + dense-cosine-distance pair under the selected strategy. |
| `convex_combination_score(...)` | Two-channel TM2C2 over already-normalized `[0, 1]` scores. |
| `weighted_convex_combination_score(scores, weights)` | N-channel convex fusion over already-normalized scores and explicit weights. |
| `weighted_convex_fuse(results, weights, limit=None)` | Fuse complete normalized-score lists with deterministic ordering and contribution-level audit records. |
| `FusedScoredItem`, `WeightedChannelContribution` | Immutable complete-list convex result and its per-channel evidence. |
| `reciprocal_rank_fusion_score(ranks, eta=60)` | RRF over positive integer 1-based per-channel ranks. |
| `reciprocal_rank_fuse(rankings, eta=60, limit=None)` | Fuse complete ranked item-ID lists with deterministic ordering and a rank audit trail. |
| `FusedRankedItem` | Immutable complete-list RRF result (`item_id`, `score`, `channel_ranks`). |
| `weighted_reciprocal_rank_fusion_score(ranks, weights, eta=60)` | Weighted RRF for one candidate under a fixed convex channel policy. |
| `weighted_reciprocal_rank_fuse(rankings, weights, eta=60, limit=None)` | Fuse complete rank-only lists with deterministic ordering and contribution records. |
| `FusedWeightedRankedItem`, `WeightedRankContribution` | Immutable weighted-RRF result and its present or missing channel evidence. |
| `evaluate_ranking(ranking, judgments, cutoff=...)` | Evaluate one ranking with P@k, R@k, RR@k, and graded nDCG@k. |
| `evaluate_rankings(rankings, judgments, cutoff=...)` | Evaluate a complete query set with per-query metrics and macro averages. |
| `RankingMetrics`, `QueryRankingMetrics` | Immutable single-ranking and query-associated metric records. |
| `AggregateRankingMetrics`, `RankingEvaluationReport` | Immutable macro metrics and complete evaluation audit report. |
| `theoretical_min_max_normalize(score, bounds)` | Scale a score to `[0, 1]` using a scoring function's theoretical bounds. |
| `normalize_search_text(text)` | NFC-compose + whitespace-collapse + length-cap a query. |
| `WORD_SIMILARITY_THEORETICAL_BOUNDS`, `COSINE_DISTANCE_THEORETICAL_BOUNDS` | `(lower, upper)` tuples for the common lexical/dense pairing. |

## The normalization contract

Character-trigram lexical retrieval is language-agnostic only if query
and documents fold **identically**. `normalize_search_text` owns the
query side (NFC). Do accent-folding + lowercasing on the **store** side,
in one place, and call it from both — e.g. a PostgreSQL `IMMUTABLE`
wrapper `lower(unaccent(normalize(text, NFC)))` used in a `pg_trgm` GiST
expression index. rankweave stays out of your store so the two sides
cannot silently diverge.

## Research grounding

- **Bruch, Gai & Ingber (2023).** *An Analysis of Fusion Functions for
  Hybrid Retrieval.* ACM TOIS 42(1). arXiv:2210.11934. — TM2C2 > RRF;
  theoretical-normalization stability; extension from two retrieval systems
  to multiple systems; and the fusion desiderata (monotonicity, homogeneity,
  boundedness, Lipschitz continuity, sample efficiency) this library's
  defaults satisfy.
- **Cormack, Clarke & Büttcher (2009).** *Reciprocal Rank Fusion
  outperforms Condorcet and individual Rank Learning Methods.* SIGIR
  2009. — RRF definition, η = 60.
- **Samuel et al. (2025).** *MMMORRF: Multimodal Multilingual Modularized
  Reciprocal Rank Fusion.* SIGIR 2025. DOI: 10.1145/3726302.3730157. —
  evidence that weighted RRF can improve retrieval when channels have
  different reliability. RankWeave exposes generic fixed convex weights,
  not the paper's video-specific adaptive estimator.
- **Järvelin & Kekäläinen (2002).** *Cumulated Gain-based Evaluation of IR
  Techniques.* ACM TOIS 20(4). DOI: 10.1145/582415.582418. — graded gain,
  rank discounting, and normalization by an ideal ranking.
- **NIST `trec_eval`** — reference conventions for precision at a fixed
  cutoff, recall, and first-relevant reciprocal rank.
- **UAX #15**, Unicode Normalization Forms — NFC composition.

PDFs and a citation manifest live in [`docs/research/`](docs/research/).

## Development

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report    # 100% line + branch coverage required
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
