# Explicit-fold convex fusion cross-validation

RankWeave can evaluate the complete fixed-policy selection procedure for convex
scored-channel fusion using caller-owned blocked folds. Every fold tunes only on
the complementary queries, applies the selected policy unchanged to its held-out
queries, and preserves both training-selection and held-out evidence. The API is
standard-library-only, deterministic, store-agnostic, and suitable as a
standalone experiment primitive or a naruon/MSA module.

## Why fold assignments are explicit

Random folds are not universally safe. Retrieval queries can be dependent
because they are translations, paraphrases, revisions, repeated requests from
one user or tenant, synthetic variants of one source, or observations from the
same project, customer, event, or time window. Splitting these families across
training and held-out data can leak information and understate deployment error.

RankWeave therefore does not generate folds. The caller provides one fold ID for
every query and owns the scientific claim that the blocking reflects the target
deployment boundary. The report preserves the exact assignments through each
fold's ordered training and held-out query identifiers.

## Complete grouped example

```python
from rankweave import cross_validate_weighted_convex_fusion

report = cross_validate_weighted_convex_fusion(
    {
        "query-a1": {
            "lexical": [("a", 1.0), ("x", 0.0)],
            "dense": [("x", 1.0), ("a", 0.0)],
        },
        "query-b1": {
            "lexical": [("y", 1.0), ("b", 0.0)],
            "dense": [("b", 1.0), ("y", 0.0)],
        },
        "query-a2": {
            "lexical": [("c", 0.9), ("z", 0.1)],
            "dense": [("z", 0.9), ("c", 0.1)],
        },
        "query-b2": {
            "lexical": [("w", 0.9), ("d", 0.1)],
            "dense": [("d", 0.9), ("w", 0.1)],
        },
    },
    {
        "query-a1": {"a": 3},
        "query-b1": {"b": 3},
        "query-a2": {"c": 3},
        "query-b2": {"d": 3},
    },
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    {
        "query-a1": "source-family-a",
        "query-b1": "source-family-b",
        "query-a2": "source-family-a",
        "query-b2": "source-family-b",
    },
    cutoff=1,
)

assert len(report.folds) == 2
assert report.out_of_fold_evaluation.aggregate.query_count == 4
print(report.final_tuning.best_policy_id)
```

The fold mapping deliberately keeps each source family together. Fold order is
the first appearance of each fold ID in the scored-query mapping, and query
order inside every training, held-out, and out-of-fold result follows the
original scored-query order.

## Report interpretation

Each `WeightedConvexCrossValidationFold` contains:

- `fold_id`: the caller's immutable fold identifier;
- `training_query_ids`: the exact queries used for policy selection;
- `held_out_query_ids`: the exact queries excluded from tuning and used only for
  fold assessment;
- `tuning`: the complete `WeightedConvexTuningReport` from the training queries;
- `held_out_evaluation`: the complete evaluation after applying the selected
  training policy unchanged to the held-out queries.

`WeightedConvexCrossValidationReport` contains two deliberately different
summaries:

- `out_of_fold_evaluation` reconstructs all held-out rankings in original query
  order and estimates the observed selection procedure under the supplied fold
  design;
- `final_tuning` uses all judged queries to recommend one fixed policy for future
  use. Its objective is a full-data selection score, not a held-out estimate.

Do not report `final_tuning.best_objective_score` as cross-validated
performance. Use `out_of_fold_evaluation` for that descriptive purpose and keep
the fold-level evidence for audit.

## Choosing leakage-aware folds

Use a common fold ID for observations that must not cross the experimental
boundary. Depending on the deployment question, this may include:

- paraphrases or multilingual translations of one information need;
- repeated requests from one person, account, tenant, or session family;
- document revisions or derivatives from one source artifact;
- synthetic augmentations and their originating query;
- queries associated with one customer, project, event, or opportunity;
- observations from the same time block.

Explicit assignments do not prove that the split is scientifically valid. They
make the split reviewable and prevent a library from silently applying a random
scheme that ignores domain structure.

For forecasting, future observations must not influence earlier training
windows. Symmetric blocked folds are not automatically rolling-origin evidence.
Construct chronological folds that respect the availability cutoff, or use a
dedicated forward-chaining design outside this API.

## Fail-closed contract

Cross-validation requires:

- a positive integer cutoff;
- one supported aggregate tuning objective;
- at least one candidate policy;
- exactly matching, non-empty scored-query, judgment-query, and fold-assignment
  sets;
- at least two distinct hashable fold identifiers.

Score, weight, duplicate-item, undeclared-channel, relevance, and query
validation delegate to RankWeave's established fusion, tuning, and evaluation
primitives. A fold failure returns no partial cross-validation report.

## Scope boundaries

The API deliberately does not:

- generate, shuffle, stratify, or optimize folds;
- infer users, tenants, temporal groups, translations, or duplicate families;
- normalize raw provider scores;
- generate a hidden candidate-weight grid;
- fit query-adaptive or document-adaptive policies;
- run paired statistical comparison;
- deploy the final selected policy.

These boundaries keep fold ownership, leakage assumptions, and deployment
policy explicit.

## Research grounding

Stone distinguished cross-validatory model choice from assessment. Cawley and
Talbot showed that model-selection criteria can themselves be overfit, creating
optimistic performance estimates when selection and assessment are not properly
separated. Roberts and colleagues demonstrated that random cross-validation can
be misleading under temporal, spatial, hierarchical, and related dependence and
recommended blocked strategies aligned with the data structure. Barata's 2026
retrieval preprint applies query-level fold selection to hybrid fusion and keeps
training-selected weights separate from held-out fold evaluation.

RankWeave supplies deterministic execution and evidence retention. The caller
remains responsible for defining a fold design that answers the intended
scientific and operational question.

## References — APA 7th edition

Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch
retrieval? Cross-validated weighted RRF with paired inference and cross-domain
transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and
subsequent selection bias in performance evaluation. *Journal of Machine
Learning Research, 11*, 2079–2107.
https://www.jmlr.org/papers/v11/cawley10a.html

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J.,
Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B.,
Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F.
(2017). Cross-validation strategies for data with temporal, spatial,
hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929.
https://doi.org/10.1111/ecog.02881

Stone, M. (1974). Cross-validatory choice and assessment of statistical
predictions. *Journal of the Royal Statistical Society: Series B
(Methodological), 36*(2), 111–133.
https://doi.org/10.1111/j.2517-6161.1974.tb00994.x
