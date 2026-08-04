# Direct TREC Run Comparison Design

## Goal

Add one dependency-free API that accepts a baseline TREC run, a candidate TREC
run, and one qrels artifact and returns a complete immutable comparison record
containing the parsed artifacts, both ranking evaluations, and paired
randomization evidence.

## Buyer problem

RankWeave 0.7.0 can parse TREC artifacts and can statistically compare native
ranking mappings, but benchmark users still have to manually connect five
operations:

1. parse the baseline run;
2. parse the candidate run;
3. parse qrels;
4. convert both runs to score-ordered ranking mappings;
5. call `compare_rankings` with the correct metric and randomization options.

That glue is easy to implement inconsistently. It can discard run IDs, evaluate
one system under a different cutoff, mis-handle negative qrels, or omit a query
before significance testing. A commercial benchmark API should make the safe
path the shortest path.

## Public API

Create `src/rankweave/trec_comparison.py` with:

```python
@dataclass(frozen=True)
class TrecRunComparisonReport:
    baseline_run: TrecRun
    candidate_run: TrecRun
    qrels: TrecQrels
    comparison: RankingComparisonReport[str]


def compare_trec_runs(
    baseline_run_text: str,
    candidate_run_text: str,
    qrels_text: str,
    *,
    cutoff: int,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> TrecRunComparisonReport:
    ...
```

The complete parsed artifacts are retained rather than only their tags. This
allows callers to format, archive, inspect, or trace every source record from
the returned object without reparsing untrusted text.

## Data flow

1. Parse the baseline run with `parse_trec_run`.
2. Parse the candidate run with `parse_trec_run`.
3. Parse qrels once with `parse_trec_qrels`.
4. Convert each run to decreasing-score rankings through
   `TrecRun.rankings_by_query()`.
5. Convert qrels to the generic non-negative evaluation mapping through
   `TrecQrels.relevance_by_query()`.
6. Call `compare_rankings` with the shared cutoff, metric, alternative, draw
   count, and seed.
7. Return the three immutable parsed artifacts and the immutable comparison.

No duplicate implementation of evaluation or randomization is permitted.

## Validation and error handling

Existing lower-level contracts remain authoritative:

- malformed TREC records fail with physical line numbers;
- run scores are finite and rankings are score-ordered;
- qrels relevance is a signed integer in `[-127, 127]`;
- negative qrels remain audited but are omitted from generic evaluation;
- each run must have one tag and no duplicate query/document or query/rank;
- each evaluation requires exactly the same query IDs as qrels;
- comparison requires the same positive cutoff and supported metric,
  alternative, seed, and randomization count.

`compare_trec_runs` does not catch or rewrite these `ValueError` messages. A
caller should receive the precise parser, evaluation, or comparison error that
identifies the broken artifact or option.

Baseline and candidate run tags are not required to differ. Some external
pipelines reuse tags; rejecting them would prevent valid comparisons. The
returned artifacts make identical tags visible for audit.

## Determinism

The function inherits RankWeave's existing deterministic contracts:

- decreasing score order;
- source order for exact score ties;
- baseline query order in per-query comparison evidence;
- exact sign enumeration for at most 16 non-zero differences;
- local seeded Monte Carlo randomization above that limit;
- no global random-state mutation.

## Testing

Tests must cover:

- a hand-checked end-to-end comparison from three TREC strings;
- source comments and score-order conversion;
- retention of baseline run, candidate run, qrels, and run IDs;
- identical run IDs remaining allowed and visible;
- query-set mismatch propagation for baseline and candidate independently;
- malformed baseline run, candidate run, and qrels errors;
- metric, alternative, draw-count, and seed pass-through;
- exact and Monte Carlo method selection;
- immutability of the top-level result;
- package-root export;
- wheel content and installed-wheel smoke use;
- 100% production line and branch coverage and complete production docstrings.

## Architecture

The new module is a thin orchestration boundary. `trec.py` remains responsible
for interchange parsing and formatting. `comparison.py` remains responsible for
native ranking evaluation and paired significance. This avoids making the
already substantial TREC parser own statistical policy and keeps each file
independently understandable and testable.

The runtime remains standard-library-only and store-agnostic.

## Documentation and release

Update README, AGENTS, CHANGELOG, research/standards documentation, package-root
exports, wheel checks, and the installed-wheel smoke test. Release metadata
advances from `0.7.0` to `0.8.0` only after the exact PR head passes repository
policy.

## Non-goals

This slice does not add path-based file I/O, streaming multi-gigabyte artifacts,
multiple-testing correction, confidence intervals, effect-size thresholds,
HTML reports, CLI commands, or automatic benchmark downloads.
