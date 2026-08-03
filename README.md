# rankweave

**Language-agnostic hybrid-retrieval score fusion — pure-Python, store-agnostic.**

`rankweave` decides *how to combine* scores from lexical, dense,
learned-sparse, and other retrieval channels into one ranking. It ships
research-grounded convex score fusion for two or more normalized channels,
Reciprocal Rank Fusion for rank-only channels, and the query-side Unicode
normalization that makes character-level lexical matching language-agnostic.
It has **no dependencies** (stdlib only) and **no opinion about your store** —
bring your own channels; rankweave fuses their evidence.

It is extracted, unchanged in behavior, from the Context Search engine of
[naruon](https://github.com/ContextualWisdomLab/naruon), following the
lab's ONE SOURCE MULTI USE convention: standalone product *and*
submodule-importable.

## Why

A convex combination of **theoretically** min-max normalized scores
(TM2C2) beats Reciprocal Rank Fusion in- and out-of-domain, is robust
for `alpha ∈ [0.6, 0.8]` with no training data, and — unlike rank
fusion — preserves the score distribution (Bruch, Gai & Ingber 2023).
Their two-system analysis also extends directly to multiple retrieval
systems. RRF remains available for channels that expose only ranks. See
[`docs/research/`](docs/research/) for the grounding.

## Install

```bash
pip install rankweave
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

## API

| Symbol | Purpose |
|---|---|
| `FusionSettings` | Immutable strategy + parameters (`strategy_name`, `semantic_weight_alpha`, `rank_constant_eta`). |
| `fuse_channel_scores(...)` | Fuse the common lexical-word-similarity + dense-cosine-distance pair under the selected strategy. |
| `convex_combination_score(...)` | Two-channel TM2C2 over already-normalized `[0, 1]` scores. |
| `weighted_convex_combination_score(scores, weights)` | N-channel convex fusion over already-normalized scores and explicit weights. |
| `reciprocal_rank_fusion_score(ranks, eta=60)` | RRF over 1-based per-channel ranks. |
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
- **UAX #15**, Unicode Normalization Forms — NFC composition.

PDFs and a citation manifest live in [`docs/research/`](docs/research/).

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q          # no external services
python -m ruff check .
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
