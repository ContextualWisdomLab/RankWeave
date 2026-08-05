# Convex score-fusion policy tuning

RankWeave can select one fixed convex score-fusion policy from a caller-defined,
insertion-ordered policy family using judged validation queries. The selector is
standard-library-only, store-agnostic, deterministic, and suitable as either a
standalone experiment primitive or a naruon/MSA module.

## Input contract

`tune_weighted_convex_fusion` accepts:

- normalized scored result lists for every validation query and retrieval
  channel;
- exactly matching query-level relevance judgments;
- one ordered mapping of policy identifiers to convex channel weights;
- a positive evaluation cutoff;
- one supported aggregate objective.

Every supplied score must be finite and within `[0, 1]`. Weights must be finite,
non-negative, and sum to one. A channel present in a query result must have a
weight. A policy may assign weight to a channel absent from one query; missing
evidence contributes zero, matching `weighted_convex_fuse`.

RankWeave does not normalize provider scores inside the selector. Apply a stable,
documented normalization before constructing the scored result lists. The
built-in theoretical normalization helpers are appropriate when a scoring
function has known bounds.

## Complete example

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
        "balanced": {"lexical": 0.5, "dense": 0.5},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=1,
)

assert report.best_policy_id == "lexical-heavy"
assert report.best_channel_weights == (
    ("lexical", 0.9),
    ("dense", 0.1),
)
```

## Evidence retained

Each `WeightedConvexTuningTrial` preserves:

- the caller's policy identifier;
- the channel weights in caller order;
- the selected aggregate objective score;
- the complete immutable `RankingEvaluationReport`, including every per-query
  metric.

`WeightedConvexTuningReport` preserves all trials in candidate order and records
the best policy, weights, score, cutoff, and objective. A later candidate must
have a strictly greater objective to replace the current best, so the first
policy wins an exact tie.

Supported objectives are:

- `mean_ndcg_at_k`;
- `mean_reciprocal_rank_at_k`;
- `mean_recall_at_k`;
- `mean_precision_at_k`.

## Validation and test separation

Define the candidate policy family before inspecting results. The selector
estimates which fixed policy performs best on the supplied validation judgments;
it does not provide an unbiased estimate of the selected policy's future
performance.

After selecting a policy:

1. freeze its exact channel weights;
2. run it once on an independent held-out test query set;
3. report effect sizes and paired uncertainty against the relevant baseline;
4. retain validation and test artifacts separately.

Selecting and reporting on the same queries is a resubstitution estimate and can
be optimistic. For cross-validation, the caller should split queries, call the
selector on each training fold, and apply the selected fixed policy unchanged to
the corresponding held-out fold.

## Scope boundaries

The selector deliberately does not:

- create a simplex or random search grid;
- fit query-adaptive or document-adaptive weights;
- normalize raw lexical or embedding scores;
- choose train/validation/test partitions;
- compare the selected policy statistically;
- mutate or deploy a live retrieval configuration.

These boundaries keep the core deterministic, dependency-free, auditable, and
reusable across storage and serving platforms.

## Research grounding

Bruch, Gai, and Ingber found that convex combination can outperform RRF in
in-domain and out-of-domain hybrid retrieval and can be tuned with relatively
few examples. Barata's recent Dutch retrieval preprint illustrates a stricter
selection protocol: define a finite simplex, select only on training folds,
measure out-of-fold behavior, and distinguish an apparent full-data optimum from
held-out performance. RankWeave implements the finite deterministic selection
primitive; experiment splitting and inference remain explicit caller
responsibilities.

## References — APA 7th edition

Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch
retrieval? Cross-validated weighted RRF with paired inference and cross-domain
transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for
hybrid retrieval. *ACM Transactions on Information Systems, 42*(1), Article 20,
1–35. https://doi.org/10.1145/3596512
