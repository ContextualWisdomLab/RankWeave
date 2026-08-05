# ADR 0003: Use availability time for forward-only fusion-policy backtesting

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** Temporal assessment of fixed convex score-fusion policies

## Context

Blocked cross-validation can keep related queries together, but symmetric folds may train on observations that occur after another fold's assessment period. That design does not reproduce a production decision made with only historically available evidence.

Event time, document time, indexing time, and evidence availability time are not interchangeable. A later artifact may describe an earlier event, so ordering experiments by event time alone can leak information that was not yet known.

## Decision

RankWeave uses explicit caller-supplied `available_time_by_query` values and ordered assessment-window definitions for temporal backtesting.

- Availability values must be timezone-aware `datetime` instances and are normalized to UTC.
- Every training timestamp must be strictly earlier than every held-out timestamp in its window.
- Held-out windows are disjoint and strictly ordered.
- The first window's training queries form the initial warm-up set.
- Every remaining query is held out exactly once.
- Earlier held-out queries may enter later training windows, supporting expanding or rolling retention designs.
- RankWeave does not infer availability, generate windows, or equate this procedure with causal inference.

Each window selects one policy on its declared historical training set, applies the selected weights unchanged to the future held-out set, and retains exact rankings plus a complete evaluation. The aggregate report separates out-of-sample assessment from an all-data final tuning recommendation.

## Consequences

- Future-information leakage becomes an executable validation failure.
- The buyer's retraining cadence and retention policy remain visible in the input artifact.
- Same-time evidence cannot be split across training and held-out sets.
- Expanding and sliding windows are both representable.
- Availability provenance remains a consumer responsibility.
- The API stays standard-library-only, deterministic, store-agnostic, and reusable by naruon or another MSA.

## Rejected alternatives

- **Ordinary blocked cross-validation:** does not enforce forward-only evidence.
- **Automatic window generation:** hides deployment-specific retraining and retention choices.
- **Naive datetimes:** require an implicit timezone and can change ordering.
- **Event-time ordering:** can admit evidence that was published or discovered later.
- **All-data tuning score as performance:** conflates policy selection with prospective assessment.

## References — APA 7th edition

Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. *Information Sciences, 191*, 192–213. https://doi.org/10.1016/j.ins.2011.12.028

Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: An empirical study on performance estimation methods. *Machine Learning, 109*(11), 1997–2028. https://doi.org/10.1007/s10994-020-05910-7

Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting, 16*(4), 437–450. https://doi.org/10.1016/S0169-2070(00)00065-0
