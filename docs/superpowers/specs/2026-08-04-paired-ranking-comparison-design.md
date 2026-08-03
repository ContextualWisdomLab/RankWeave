# Paired Ranking Comparison Design

## Goal

Add a dependency-free, fail-closed API that compares two retrieval systems on
exactly the same judged query set and reports both the observed per-query metric
differences and a paired Fisher randomization p-value.

## Buyer problem

RankWeave can fuse, evaluate, and tune rankings, but a buyer still has to move
per-query values into another statistics package to decide whether an observed
mean lift is distinguishable from topic-sampling noise. That handoff is easy to
misalign by query ID, accidentally drop difficult queries, or report a metric
increase without uncertainty evidence.

## Public API

Create `src/rankweave/comparison.py` with:

```python
compare_ranking_reports(
    baseline_report,
    candidate_report,
    *,
    metric_name="ndcg_at_k",
    alternative="two-sided",
    randomization_count=10_000,
    random_seed=0,
) -> PairedRandomizationResult

compare_rankings(
    baseline_rankings_by_query,
    candidate_rankings_by_query,
    relevance_by_query,
    *,
    cutoff,
    metric_name="ndcg_at_k",
    alternative="two-sided",
    randomization_count=10_000,
    random_seed=0,
) -> RankingComparisonReport
```

Supported metric names:

- `precision_at_k`
- `recall_at_k`
- `reciprocal_rank_at_k`
- `ndcg_at_k`

Supported alternatives:

- `two-sided`
- `candidate-greater`
- `candidate-less`

Public frozen records:

- `QueryMetricDifference`: query ID, baseline value, candidate value, and
  candidate-minus-baseline difference.
- `PairedRandomizationResult`: metric, alternative, query counts, means,
  observed difference, p-value, method, number of randomizations, seed, and
  complete per-query differences.
- `RankingComparisonReport`: baseline evaluation, candidate evaluation, and
  paired significance result.

## Statistical method

For each query, compute candidate minus baseline. Under the paired null
hypothesis, exchangeability permits independently flipping the sign of every
non-zero difference.

- When the number of non-zero differences is at most 16, enumerate all `2**n`
  sign assignments exactly.
- Above 16, draw `randomization_count` deterministic sign assignments using a
  local `random.Random(random_seed)` instance.
- For Monte Carlo p-values, use the plus-one correction
  `(extreme + 1) / (draws + 1)` so a finite simulation never reports zero.
- For exact p-values, use `extreme / total`.
- Compare signed sums rather than means because query count is constant.
- A tolerance of `1e-15` prevents a numerically equal permutation from being
  excluded by floating-point roundoff.
- If every query difference is zero, return `p_value=1.0` with method `exact`
  and one evaluated assignment.

The default is a two-sided test. One-sided alternatives are explicit and refer
to the candidate system.

## Validation

Comparison fails closed unless:

- both inputs are `RankingEvaluationReport` instances;
- both use the same positive cutoff;
- both contain at least one query;
- each report has unique, hashable query IDs;
- every query metric cutoff equals the report cutoff;
- both reports contain exactly the same query IDs;
- the selected metric is supported and finite in `[0, 1]`;
- `randomization_count` is a positive integer;
- `random_seed` is an integer and not a boolean;
- the alternative is supported.

Query order in the result follows the baseline report. Candidate values are
joined by query ID, never by position.

## Architecture

The comparison module depends only on `evaluation.py` and `_validation.py`.
The existing evaluation module remains responsible for ranking metrics. The new
module owns report alignment, paired differences, and randomization. The
convenience `compare_rankings` path evaluates both systems through the existing
fail-closed `evaluate_rankings` contract before comparison.

No runtime dependency, database, network, or global random state is introduced.

## Testing

Tests must cover:

- hand-computed exact two-sided and one-sided p-values;
- query-ID alignment independent of candidate order;
- deterministic Monte Carlo results for the same seed;
- all-zero differences;
- exact/Monte Carlo method boundary;
- unsupported metrics and alternatives;
- cutoff, query-set, duplicate-ID, unhashable-ID, metric-domain, seed, and
  randomization-count failures;
- immutability of all public records;
- end-to-end `compare_rankings` evaluation;
- package-root exports, wheel contents, and installed-wheel smoke use;
- 100% production line and branch coverage and complete production docstrings.

## Research grounding

Smucker, Allan, and Carterette (CIKM 2007, DOI
`10.1145/1321440.1321528`) compared common significance tests on TREC runs and
found little practical difference among randomization, bootstrap, and paired
t-tests, while reporting poor behavior for sign and Wilcoxon tests in this use
case. RankWeave selects the paired randomization test because it is
non-parametric, directly reflects paired topic exchangeability, and can be
implemented transparently without a numerical dependency.

## Non-goals

This slice does not add multiple-comparison correction, confidence intervals,
Bayesian inference, online A/B testing, power analysis, or claims that
statistical significance implies practical or commercial significance.
