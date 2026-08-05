# Temporal convex-fusion backtesting design

## Status

Approved for implementation under RankWeave's standing commercialization loop.

## Problem

RankWeave 0.16.0 supports caller-owned blocked cross-validation, but symmetric folds do not simulate a production system that learns only from evidence available before a future assessment period. Buyers need a deterministic answer to this question:

> If a fusion policy had been selected using only evidence available before each assessment window, how would it have performed on the next unseen queries?

## Public API

Add `rankweave.temporal_backtesting` with:

- `WeightedConvexBacktestWindowDefinition`
- `WeightedConvexBacktestWindow`
- `WeightedConvexBacktestReport`
- `backtest_weighted_convex_fusion`

Inputs are normalized scored results, exactly matching judgments, an ordered finite convex policy family, one timezone-aware availability timestamp per query, ordered window definitions, a cutoff, and a supported objective.

## Time semantic

`available_time_by_query` is the earliest instant at which the complete evidence supplied to the experiment was available to policy selection. It is not event time, document creation time, indexing time, or a later revised timestamp.

Only timezone-aware `datetime` values are accepted. Values are normalized to UTC. Naive datetimes fail closed because assuming a timezone would change the experiment boundary.

## Window contract

Each definition contains a window identifier, training query IDs, and held-out query IDs. Windows are processed in sequence order.

Every window requires:

- a unique hashable identifier;
- non-empty, unique training and held-out query IDs;
- no within-window overlap;
- known query IDs only;
- `max(training_available_time) < min(held_out_available_time)`;
- held-out query sets disjoint across windows;
- strictly ordered held-out time ranges.

The strict inequality prevents observations sharing one availability instant from being split between training and assessment.

The first window's training queries form the initial warm-up set. Every input query must be either in that set or held out exactly once. Earlier held-out queries may enter later training windows, allowing expanding or sliding windows, but an initial warm-up query may not later become held out.

## Execution

For each window RankWeave:

1. tunes policies on declared training queries only;
2. freezes the selected weights;
3. fuses held-out queries with those weights unchanged;
4. preserves exact held-out rankings;
5. evaluates the complete held-out set;
6. records UTC training and held-out time bounds.

The final report reconstructs exact out-of-sample rankings in original input-query order, evaluates the complete assessed set, and separately runs all-data final tuning. Final tuning is a future policy recommendation, not out-of-sample evidence.

## Validation

Fail closed for mismatched query universes, non-datetime or naive timestamps, duplicate IDs, empty windows, unknown queries, training/held-out overlap, same-time or future training evidence, repeated held-out queries, non-monotone held-out ranges, omitted queries, invalid cutoff or objective, malformed policies, scores, or result lists.

Existing fusion, tuning, and evaluation APIs remain the numerical source of truth.

## Architecture

The module is standard-library-only and accepts in-memory data. It performs no filesystem, database, network, provider, scheduler, or LLM access. It remains deterministic, store-agnostic, standalone-usable, and importable by naruon or another MSA consumer.

The package version advances to 0.17.0 because public runtime APIs are added.

## Research boundary

Rolling-origin and repeated out-of-sample evaluation preserve temporal order and expose model-update choices. The implementation adopts the narrow engineering implication that future evidence cannot enter an earlier policy-selection window. It does not claim that retrieval queries form a classical univariate time series or that this backtest alone proves stationarity, causality, or commercial value.

## References — APA 7th edition

Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. *Information Sciences, 191*, 192–213. https://doi.org/10.1016/j.ins.2011.12.028

Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: An empirical study on performance estimation methods. *Machine Learning, 109*(11), 1997–2028. https://doi.org/10.1007/s10994-020-05910-7

Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting, 16*(4), 437–450. https://doi.org/10.1016/S0169-2070(00)00065-0

## Verification

The exact head must pass Python 3.10–3.13, Ruff, compileall, the full tests, 100% production statement and branch coverage, complete production docstrings, package and installed-wheel smoke, Security Scan, SAST, and zero unresolved review threads.
