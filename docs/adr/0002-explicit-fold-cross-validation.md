# ADR 0002: Require caller-owned blocked folds for policy-selection assessment

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** Convex score-fusion policy selection and out-of-fold evaluation

## Context

RankWeave 0.15.0 can select one fixed convex channel-weight policy from a caller-defined finite policy family on judged validation queries. Reporting the best objective from that same validation set as future performance would conflate policy choice with assessment and can introduce selection bias.

Random query-level folds are also unsafe whenever observations share a user, tenant, event, project, source document, translation family, revision lineage, synthetic augmentation family, or time block. RankWeave cannot infer those domain relationships from item and query identifiers alone.

## Decision

RankWeave exposes explicit blocked cross-validation through `cross_validate_weighted_convex_fusion`.

The caller supplies one fold identifier for every query. Fold identifiers are interpreted in first-query appearance order and must define at least two non-empty folds. For each held-out fold, RankWeave:

1. tunes the finite policy family only on complementary training queries;
2. applies the selected fixed weights unchanged to held-out scored results;
3. retains the complete training tuning report and held-out evaluation;
4. reconstructs one out-of-fold evaluation in original query order.

The report also contains a separate all-data `final_tuning` recommendation for future use. That recommendation is not held-out evidence.

The implementation delegates to `tune_weighted_convex_fusion`, `weighted_convex_fuse`, and `evaluate_rankings`; it does not duplicate fusion or metric arithmetic. RankWeave does not generate random folds, infer grouping structure, or claim that caller-supplied folds are leakage-safe.

## Consequences

- Dependence-aware fold design remains explicit, auditable, and owned by the consuming domain.
- Translations, paraphrases, revisions, users, tenants, projects, events, and time blocks can be kept together when required.
- Out-of-fold effectiveness is separated from the all-data deployment recommendation.
- Symmetric blocked cross-validation is not described as rolling-origin forecasting or future-time validation.
- Consumers must retain the fold assignment alongside the reported evidence and must use an independent temporal design when deployment is forward-looking.
- Runtime remains standard-library-only, deterministic, store-agnostic, and reusable as a standalone package or naruon/MSA module.

## Rejected alternatives

- **Report the full-data tuning optimum:** rejected because it is selection evidence, not an unbiased assessment.
- **Generate random folds inside RankWeave:** rejected because the library cannot know the dependence structure and could silently leak related observations.
- **Infer groups from identifier strings:** rejected because naming conventions are not a reliable statistical contract.
- **Implement a numerical optimizer or nested model framework:** rejected because the current bounded slice selects among explicit fixed policies and should remain transparent and dependency-free.

## Research basis

- Stone (1974) distinguishes cross-validatory choice from assessment.
- Cawley and Talbot (2010) document over-fitting of model-selection criteria and subsequent selection bias.
- Roberts et al. (2017) show that random cross-validation can underestimate error under temporal, spatial, hierarchical, or related dependence.
- Barata (2026, preprint) provides a retrieval-specific example of fold-local fusion-weight selection and held-out evaluation.

Full APA 7th edition references are maintained in `docs/research/README.md`.
