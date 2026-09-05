# Paired-p95 order-statistic selection profile

Status: local calculation evidence for proposed PR #41, not released software,
an admitted statistical design, or a gateway performance result.

## Question and decision

Can the existing replay operation spend less time computing the same report?
The scalar quantiles need only one order statistic each. Full sorting orders
values that no consumer observes. Reuse standard-library in-place selection
with `f64::total_cmp`, preserving signed zeros and the integer type-1 ranks;
do not add an estimator, dependency, RNG, cache or parallel execution policy.

Keep the change only if the matched-build median complete API call time falls,
every complete-report digest stays identical, and all existing quality gates
pass. The baseline is `9375287982912fffe96c269c309f70fe518cfafd`; the candidate is
`511019f6d97788ac52a04ea01ea3167e1fe3d6ff`. The unsorted-values/signed-zero
selection regression failed at `0836d79` and passes in the candidate. A profiler
JSON-to-tuple adapter failure was separately reproduced and fixed at `3f71d39`.

## Observed workload, not a synthetic policy experiment

Use `ulab-ai/xRouteBench` revision
`ea4b6e1b29d9a734f55f0a637baf326bad6aa681`, configuration `llmrouter_generic`,
file `test.parquet`. Its SHA-256 must be
`cc7f33f03298c734c1f4b3c380d8d9b84dc8723eb0d08f850de033d2645778f4`.
The existing cached PyArrow **25.0.0** reader decoded this file offline; no
reader was installed or added to RankWeave. This differs from the reader
version recorded in CO's earlier observation audit.

Construct the request deterministically:

1. Read all 67,122 rows in file order; retain `response_time` without any
   filtering on answer, score, token count or presumed success.
2. Identify a scored task with the SHA-256 of UTF-8 JSON containing, in order,
   `task_name`, `query`, `choices`, `metric`, `ground_truth`; serialize with
   `ensure_ascii=False` and compact separators. Keep first-seen task order.
   Require 3,729 tasks, the same 18 model names per task, and no duplicate
   task/model cell. Do not use nullable `task_id` alone.
3. Sort model names lexicographically. Pair adjacent names into nine numeric
   pairs per task. Give each pair the opaque ID `task_digest-pair_index`
   (zero-based index), and put all nine IDs in one complete task unit. This
   covers every source row exactly once; it is **not** a meaningful baseline/
   candidate routing policy or an assertion of independent task units.
4. Outside the library, initialize Python `random.Random(20260905)`. Build
   50 draws, each with 3,729 calls to `randrange(3729)`. Each draw expands all
   nine pairs of every selected task. Set `max_resample_observations=33561`.
5. JSON-encode the existing API keyword arguments in insertion order:
   `observation_pairs`, `resampling_units`, `unit_draws`,
   `max_resample_observations`, using default separators and `allow_nan=False`.
   The exact request-file SHA-256 is
   `2945a4ec24f97d32abd11ba6bf38f28f41698aeef413b08c50f508abe70d748e`.

The local request and source rows are not committed or redistributed. Timing
records and evidence digests contain no prompts, answers or row-level values.
Dataset redistribution permission and timing/terminal-outcome provenance
remain unestablished; this experiment does not relax either requirement.

## Measurement and reproducibility

Build both source revisions with the same locked dependencies and optimized
Rust 1.97.1 / Maturin release-wheel path. Install into separate existing local
environments using the same Python 3.13.14 interpreter. Use the same profiler
script for both wheels, without importing the checkout as the package:

```sh
env -i PATH=/usr/bin:/bin /absolute/path/to/wheel-environment/bin/python -I \
  scripts/profile_paired_p95.py 9 < /absolute/path/to/replay-request.json
```

Run under the platform's network-denying sandbox. The recorded run used
macOS 26.5.1 arm64. Stop the isolated Linux verification container before
profiling; no compilation or test run was launched by this task during timing.
No CPU-exclusive allocation is claimed.

Execute six paired process rounds: baseline then candidate in rounds 0/2/4,
candidate then baseline in 1/3/5. Retain all nine calls from every process,
including the first. The timer surrounds the entire public replay API call,
including Python transport validation, native work and result projection.
Input preparation/imports and post-call digest serialization are outside it.

The first baseline-only nine calls had a 71.9987 ms median. An initial candidate
editable-build result was not comparable to a release wheel and was discarded
as performance evidence. The final matched-wheel experiment retained 54 calls
per version; the machine varied over time, so the complete sample list and
round ordering remain in the [measurement record](paired-p95-selection-profile.json).

| Calculation-runtime measure | Baseline | Candidate |
| --- | ---: | ---: |
| Median API wall time, all 54 calls (ms) | 91.5451 | 49.8053 |
| Round 0 median (ms) | 74.4945 | 43.9561 |
| Round 1 median (ms) | 79.4807 | 46.4346 |
| Round 2 median (ms) | 95.9779 | 72.1466 |
| Round 3 median (ms) | 98.5736 | 63.5017 |
| Round 4 median (ms) | 90.8628 | 51.0220 |
| Round 5 median (ms) | 102.2949 | 48.0900 |

The observed overall median reduction is **45.59%**. Every round's candidate
median is lower. All 108 complete reports have the same canonical-JSON digest,
`4eef2339af30a1c417478e0b56aced22e0af88070990636534358bdd3f4817b3`, and the same
input digest. The record retains both compiled-extension hashes.

## Boundaries and remaining work

This is one machine and one computation workload, without a performance
confidence interval or general speed guarantee. No gateway route-decision
time, provider p95, answer accuracy or production default is improved by this
evidence alone. Nor do the explicit resampling units establish sampling
validity, temporal independence, censoring treatment or 95% inferential
coverage. Existing Proposed ADRs and owner release/consumer gates are unchanged.

## Standard-library reference (APA 7th)

The Rust Project Developers. (n.d.). *slice::select_nth_unstable_by*.
Rust standard library documentation. Retrieved September 5, 2026, from
https://doc.rust-lang.org/std/primitive.slice.html#method.select_nth_unstable_by

The documented contract places the selected element at its sorted-order
position in place in linear time; a total-order comparator is required.
Type-1 quantile research and the inferential limits remain documented in
[the paired-p95 contract](../paired-p95-comparison.md).
