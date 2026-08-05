# Explicit-Fold Convex Fusion Cross-Validation Design

## Status

Approved for autonomous implementation under RankWeave's standing commercialization loop. This is one bounded public-API and release slice.

## Buyer-visible problem

RankWeave 0.15.0 can select a fixed convex scored-channel policy on one judged validation set, but buyers still have to reimplement the higher-level protocol that separates policy selection from held-out assessment. That gap invites two material errors:

1. reporting the selected policy's same-sample validation score as if it were prospective effectiveness; and
2. randomly splitting related, temporal, multilingual, tenant, or repeated-query observations across folds, allowing information leakage and overly optimistic estimates.

The product should execute a caller-defined blocked cross-validation protocol without generating hidden random folds. Each held-out fold must be scored only by a policy selected on the remaining queries, while a final full-data tuning report remains clearly separated as the deployment-policy recommendation rather than an unbiased test estimate.

## Research basis

Stone (1974) formalized cross-validatory choice and assessment as related but distinct uses of held-out data. Cawley and Talbot (2010) showed that optimizing a noisy model-selection criterion can itself overfit and create substantial selection bias in performance evaluation. Roberts et al. (2017) demonstrated that random cross-validation can underestimate error when temporal, spatial, hierarchical, or other dependence structures cross the train/test boundary and recommended strategically blocked folds for structured data. Barata (2026, preprint) applies query-level ten-fold selection to weighted hybrid retrieval and distinguishes training-selected weights from held-out fold effectiveness.

The RankWeave API therefore accepts explicit fold assignments. It does not create random folds, infer groups, or claim that an arbitrary caller split is leakage-safe.

## Considered approaches

### A. Random `k`-fold generation inside RankWeave

This is convenient but cannot know which queries share a user, tenant, translation family, revision chain, event, time window, or source document. Random splitting could silently leak related observations. Rejected.

### B. Evaluate every policy on every held-out fold and select the highest pooled score

This produces out-of-fold evidence for each fixed policy, but it does not estimate the performance of the policy-selection procedure that a buyer will actually run. It also risks choosing a policy after inspecting all held-out outcomes. Rejected for the first API.

### C. Caller-defined blocked folds with outer held-out evaluation and final full-data recommendation

For each explicit fold, tune only on the remaining queries, apply that selected policy unchanged to the held-out fold, and aggregate all held-out rankings into one out-of-fold evaluation. Separately tune on all queries to recommend one final fixed policy for future use. Recommended.

## Module boundary

Create `src/rankweave/cross_validation.py`. The module orchestrates existing public primitives and contains no new score-fusion or effectiveness arithmetic.

It delegates:

- training-fold policy selection to `tune_weighted_convex_fusion`;
- held-out ranking generation to `weighted_convex_fuse`;
- fold and out-of-fold metrics to `evaluate_rankings`.

## Public API

```python
@dataclass(frozen=True)
class WeightedConvexCrossValidationFold(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    fold_id: FoldIdentifier
    training_query_ids: tuple[QueryIdentifier, ...]
    held_out_query_ids: tuple[QueryIdentifier, ...]
    tuning: WeightedConvexTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]
    held_out_evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedConvexCrossValidationReport(
    Generic[FoldIdentifier, PolicyIdentifier, QueryIdentifier]
):
    cutoff: int
    objective_name: str
    folds: tuple[
        WeightedConvexCrossValidationFold[
            FoldIdentifier, PolicyIdentifier, QueryIdentifier
        ], ...
    ]
    out_of_fold_evaluation: RankingEvaluationReport[QueryIdentifier]
    final_tuning: WeightedConvexTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]


def cross_validate_weighted_convex_fusion(
    channel_results_by_query: Mapping[
        QueryIdentifier,
        Mapping[str, Sequence[tuple[ItemIdentifier, float]]],
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    fold_id_by_query: Mapping[QueryIdentifier, FoldIdentifier],
    *,
    cutoff: int,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedConvexCrossValidationReport[
    FoldIdentifier, PolicyIdentifier, QueryIdentifier
]:
    ...
```

## Processing contract

1. Validate the positive cutoff, supported objective, and non-empty policy family before fold work begins.
2. Require scored results, judgments, and fold assignments to contain exactly the same non-empty query identifiers.
3. Require every fold identifier to be hashable and at least two distinct folds.
4. Define query order from `channel_results_by_query` and fold order by first appearance in that query order.
5. For each fold:
   - preserve original query order in the training and held-out subsets;
   - tune the policy family only on the training subset;
   - reconstruct the selected channel mapping from the immutable tuning result;
   - fuse held-out queries with that fixed selected policy;
   - evaluate only the held-out judgments;
   - retain the training tuning report, query memberships, and held-out evaluation.
6. Reassemble the held-out rankings in original full-query order and evaluate one out-of-fold report.
7. Tune the same policy family on the full query set and return it as `final_tuning`.

`out_of_fold_evaluation` estimates the observed performance of the selection procedure under the supplied fold design. `final_tuning` recommends a policy using all available judged queries; its objective score is not a held-out performance estimate.

## Data-leakage boundary

The caller owns fold construction. Fold identifiers should keep all dependent observations together when the intended deployment boundary requires it, for example:

- all paraphrases or translations of one information need;
- repeated queries from one user or tenant;
- revisions derived from one source artifact;
- queries from one event, project, customer, or time block;
- near-duplicate synthetic augmentations.

RankWeave records the exact assignments but cannot infer whether the chosen grouping matches the deployment question. Temporal forecasting may require rolling-origin evaluation rather than symmetric folds; this API does not relabel blocked folds as prospective time-series evidence.

## Validation and error handling

- fewer than two distinct folds fail closed;
- a fold-assignment query mismatch reports missing assignments and extraneous assignments;
- unhashable fold identifiers fail with a stable validation error;
- invalid scores, weights, duplicate items, query mismatches, relevance values, and unsupported result channels propagate from established public primitives;
- each fold is necessarily non-empty because fold identifiers are discovered from assigned queries;
- at least two folds guarantee a non-empty training set for every fold;
- no partial report is returned after a fold error.

## Tests

Add realistic tests for:

- two blocked folds with correct training and held-out memberships;
- held-out policy application and one out-of-fold metric report;
- final full-data policy recommendation kept separate from held-out evidence;
- original query order restored after fold-major execution;
- deterministic fold order by first appearance;
- a case where different folds select different policies;
- all four objectives;
- exact first-policy ties within fold tuning;
- fold-assignment query mismatch;
- one-fold rejection;
- unhashable fold identifier rejection;
- invalid cutoff, objective, empty policies, scores, weights, and duplicate items;
- immutable public records and package-root exports.

## Documentation and release

Release as additive RankWeave `0.16.0`. Synchronize package metadata, lock metadata, public version, version tests, installed-wheel assertions, README, architecture, agent guidance, `CHANGELOG.md`, and APA 7th research references. Add an installed-wheel smoke case that executes explicit two-fold cross-validation outside the source tree.

No CLI, database, network, random-number generator, LLM, numerical dependency, or fold-generation API is added in this slice.

## References — APA 7th edition

Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch retrieval? Cross-validated weighted RRF with paired inference and cross-domain transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research, 11*, 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929. https://doi.org/10.1111/ecog.02881

Stone, M. (1974). Cross-validatory choice and assessment of statistical predictions. *Journal of the Royal Statistical Society: Series B (Methodological), 36*(2), 111–133. https://doi.org/10.1111/j.2517-6161.1974.tb00994.x
