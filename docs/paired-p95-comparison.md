# Paired p95 comparison under an explicit resampling plan

Status: proposed in PR #41 for the unreleased 0.19.0 owner package. This is a
calculation contract, not a published consumer dependency or performance claim.

## Motivation and estimand

Comparing policy latency requires the difference between each policy's p95.
The p95 of per-task differences is a different quantity. A shared task can also
have repeated attempts or related variants; distinct observation identifiers
do not establish independent sampling units.

This operation computes `candidate_p95 - baseline_p95` for the full supplied
paired observations and for every supplied resample. Both sides use exactly
the same drawn units. It does not change the existing retrieval randomization
or mean-comparison contracts.

## Runnable calculation example

```python
from rankweave import compare_paired_p95

report = compare_paired_p95(
    [("task-a", 1.0, 100.0), ("task-b", 100.0, 1.0), ("task-c", 2.0, 2.0)],
    [["task-a", "task-c"], ["task-b"]],
    [[0, 0], [1, 1], [0, 1]],
    max_resample_observations=4,
)
assert report.p95_difference == 0.0
assert report.resampled_differences == (98.0, -99.0, 0.0)
assert report.resample_observation_counts == (4, 2, 3)
```

These tiny, deliberately chosen inputs are a unit calculation example, not a
random bootstrap sample or evidence of inferential coverage. The original
policy p95s are both 100, whereas the p95 of the three paired differences is
99. Repeating the first two-observation unit expands four rows; repeating the
second one-observation unit expands two. No member of a selected unit is lost.

## Exact contract

- Each row contains a non-empty, unique opaque observation ID and two finite
  scalar values in the same caller-declared units. Missing results are not
  imputed or silently discarded; the consumer must retain the relevant failure
  denominator and justify what each observed terminal time measures.
- The declared units partition every observation exactly once. Unknown IDs,
  overlaps, empty units, and uncovered observations fail closed.
- Every resample supplies one zero-based unit index per original unit, with
  replacement. Each selected unit expands in full on both sides. There is no
  hidden RNG, independence inference, unit weighting, or dataset download.
- Each resample's expanded row count is checked against the required caller
  bound before allocation. A large unit repeated many times must not silently
  turn a small plan into an unbounded allocation.
- The p95 is the inverse empirical CDF (Hyndman–Fan type 1): sorted order
  statistic `ceil(19*n/20)`, one-based. Integer rank arithmetic avoids a
  floating-point rounding decision at an exact rank boundary. This choice
  matches the existing gateway's nearest-rank latency diagnostic; it is not
  claimed to be an unbiased or universally preferred quantile estimator.
- The interval endpoints are the inverse empirical CDF at `1/40` and `39/40`
  over the resampled p95 differences. These are a percentile-replay interval,
  not a guarantee of 95% repeated-sampling coverage. There is no BCa correction
  or simultaneous-comparison adjustment.
- Results retain the original pair/unit counts, every expanded resample count,
  every difference in draw order, point estimates, method/envelope versions,
  and a SHA-256 binding of the ordered observations, partition, plan and bound.
  The digest does not authenticate data collection, certify random draws, or
  prove that the supplied units are independent.

## Sampling and interpretation requirements

An analyst must predeclare the target population, sampling unit, failure
denominator, weighting/estimand, holdout boundaries, draw procedure, and error
or precision target. Persist the plan together with its generating protocol,
seed where applicable, collection provenance, and observation artifact digest.
The caller-supplied row bound is a resource limit, not a sample-size rule.

Unequal-sized units produce an observation-weighted empirical distribution;
this is not an equal-unit-weighted estimator. Resampling whole units supports
replay of a justified one-level cluster design, but does not validate that
design. Nested, crossed, multiple-membership, temporal or overlapping blocks,
survey weights, informative cluster sizes, missing attempts and censoring need
their own supported inferential contract. Do not flatten them into purportedly
independent units. Field and Welsh (2007) show why clustered-bootstrap validity
depends on the underlying model and method, not just resampling syntax.

Few units, few draws, discrete tails and degenerate intervals can give poor
uncertainty estimates. No universal minimum sample size or production-admission
threshold is invented here. The owner still needs design-specific calibration
and a governed release before a consumer can use this calculation in a
performance gate. A lower p95 of terminal failure times is not faster delivery
of acceptable answers; quality and completion requirements remain separate.

## Alternatives and remaining work

The existing retrieval-metric API cannot represent unrestricted measured
latencies. Reusing its `[0, 1]` scores would change the estimand. Independently
resampling the policies would discard pairing. Automatically assigning each ID
its own unit would hide a design assumption. Adding a new RNG or a Python
arithmetic fallback is unnecessary for deterministic replay of an explicit
plan. None of these alternatives is used.

The Rust owner performs validation, expansion, quantiles and subtraction; the
Python surface only validates transport values and projects an immutable
report. The existing CLI and TREC schemas are unchanged. Random plan
generation, design calibration, a generic mean migration, release acceptance,
and consumer adoption remain separate work; no open PR is a released API.

## Research grounding (APA 7th)

Hyndman, R. J., & Fan, Y. (1996). Sample quantiles in statistical packages.
*The American Statistician, 50*(4), 361–365.
https://doi.org/10.1080/00031305.1996.10473566
([author-hosted manuscript](https://robjhyndman.com/papers/sample_quantiles.pdf)).
The paper distinguishes competing sample-quantile definitions; this contract
explicitly selects type 1, not the authors' general recommendation.

Field, C. A., & Welsh, A. H. (2007). Bootstrapping clustered data.
*Journal of the Royal Statistical Society: Series B (Statistical Methodology),
69*(3), 369–390. https://doi.org/10.1111/j.1467-9868.2007.00593.x
This grounds the dependence/design limitation, not a theorem that the present
p95 replay always attains nominal coverage.

SciPy Developers. (2026). *bootstrap*. SciPy 1.18.0 manual.
https://docs.scipy.org/doc/scipy-1.18.0/reference/generated/scipy.stats.bootstrap.html
The paired option documents shared resampling indices across supplied samples.
No SciPy code or dependency is used by this implementation.

These sources are cited and summarized only: permission to redistribute their
PDFs with this package has not been established.
