# Direct TREC run comparison

`compare_trec_runs` turns three standard text artifacts into one immutable,
auditable retrieval-system comparison:

1. a baseline TREC run;
2. a candidate TREC run;
3. one shared qrels artifact.

It is the shortest safe path for benchmark users who already exchange TREC
files and want RankWeave's strict parsing, score-order evaluation, and paired
randomization without rebuilding the integration themselves.

## Example

```python
from rankweave import (
    CANDIDATE_GREATER_ALTERNATIVE,
    compare_trec_runs,
)

baseline_run = """\
q1 Q0 irrelevant 1 0.90 baseline
q1 Q0 relevant 2 0.20 baseline
"""

candidate_run = """\
q1 Q0 relevant 1 0.95 candidate
q1 Q0 irrelevant 2 0.10 candidate
"""

qrels = """\
q1 0 relevant 1
q1 0 irrelevant 0
"""

report = compare_trec_runs(
    baseline_run,
    candidate_run,
    qrels,
    cutoff=1,
    metric_name="ndcg_at_k",
    alternative=CANDIDATE_GREATER_ALTERNATIVE,
)

print(report.baseline_run.run_id)
print(report.candidate_run.run_id)
print(report.comparison.significance.mean_difference)
print(report.comparison.significance.p_value)
```

## Returned audit boundary

`TrecRunComparisonReport` is a frozen dataclass containing:

- `baseline_run`: the validated, immutable parsed baseline `TrecRun`;
- `candidate_run`: the validated, immutable parsed candidate `TrecRun`;
- `qrels`: the validated, immutable parsed `TrecQrels`;
- `comparison`: the complete `RankingComparisonReport`, including both native
  evaluations and every per-query paired metric difference.

The parsed artifacts are retained so a caller can inspect source entries, run
tags, ranks, scores, and judgments without reparsing untrusted text. A report
therefore records both the statistical result and the inputs that produced it.

## Processing sequence

The function deliberately contains no new parsing, metric, or significance
algorithm. It performs this fixed orchestration:

1. `parse_trec_run(baseline_run_text)`;
2. `parse_trec_run(candidate_run_text)`;
3. `parse_trec_qrels(qrels_text)`;
4. `TrecRun.rankings_by_query()` for each run;
5. `TrecQrels.relevance_by_query()` once;
6. `compare_rankings(...)` with the requested cutoff, metric, alternative,
   randomization count, and random seed.

That boundary keeps interchange validation in `trec.py` and paired statistical
policy in `comparison.py`.

## Validation behavior

The lower-level fail-closed contracts remain authoritative and their errors
propagate unchanged.

The comparison rejects, among other cases:

- malformed four-column qrels or six-column runs;
- non-finite scores or out-of-range qrels relevance;
- duplicate query/document judgments;
- duplicate query/document or query/rank run entries;
- inconsistent run tags within one run artifact;
- a baseline or candidate run whose query set differs from qrels;
- unsupported metrics or alternatives;
- invalid cutoff, randomization count, or seed values.

Baseline and candidate run tags do **not** have to differ. Tags are retained
provenance fields, not cryptographic identities. External pipelines sometimes
reuse a tag for several artifacts, and rejecting such inputs would make a valid
comparison impossible. Both parsed runs remain independently visible in the
returned report.

## Ordering and determinism

Submitted rank fields are validated but do not determine evaluation order.
Each run is ordered by decreasing score, following the TREC evaluation model.
Exact score ties preserve source order as RankWeave's documented deterministic
extension.

The paired comparison aligns values by query ID, never tuple position. For up
to 16 non-zero metric differences it enumerates every sign assignment exactly.
Larger comparisons use a local seeded random generator and the plus-one Monte
Carlo p-value correction. Global random state is not touched.

## Interpretation

The result exposes both the observed candidate-minus-baseline mean difference
and the paired p-value. Statistical significance does not establish that the
lift is practically important, economically valuable, robust to dataset shift,
or valid on a final held-out test set.

When a fusion policy was selected on validation data, use a separate test query
set for the final `compare_trec_runs` call. Report the mean difference, metric,
cutoff, alternative, exact or Monte Carlo method, draw count, seed, and
per-query evidence with the p-value.

## Related documentation

- [TREC interoperability](trec-interoperability.md)
- [Research grounding](research/README.md)
- [Paired comparison design](superpowers/specs/2026-08-04-paired-ranking-comparison-design.md)
- [Direct TREC comparison design](superpowers/specs/2026-08-04-trec-run-comparison-design.md)
