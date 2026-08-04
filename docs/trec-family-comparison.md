# TREC candidate-family comparison

`compare_trec_run_family` compares one baseline TREC run with a named family of
candidate runs against one shared qrels artifact. It reports every raw paired
p-value and applies Holm's step-down correction so a team can evaluate several
retrieval alternatives without silently inflating the family-wise false
positive rate.

## Example

```python
from rankweave import (
    CANDIDATE_GREATER_ALTERNATIVE,
    compare_trec_run_family,
)

baseline = """\
q1 Q0 irrelevant 1 0.90 baseline
q1 Q0 relevant 2 0.20 baseline
"""

candidate_a = """\
q1 Q0 relevant 1 0.95 model-a
q1 Q0 irrelevant 2 0.10 model-a
"""

candidate_b = """\
q1 Q0 relevant 1 0.80 model-b
q1 Q0 irrelevant 2 0.30 model-b
"""

qrels = """\
q1 0 relevant 1
q1 0 irrelevant 0
"""

report = compare_trec_run_family(
    baseline,
    {
        "semantic-model-a": candidate_a,
        "semantic-model-b": candidate_b,
    },
    qrels,
    cutoff=1,
    alternative=CANDIDATE_GREATER_ALTERNATIVE,
    familywise_alpha=0.05,
)

for candidate in report.candidates:
    print(
        candidate.candidate_id,
        candidate.comparison.significance.mean_difference,
        candidate.raw_p_value,
        candidate.holm_adjusted_p_value,
        candidate.rejected_at_familywise_alpha,
    )
```

## Returned audit evidence

`TrecRunFamilyComparisonReport` is frozen and contains:

- the parsed baseline `TrecRun`;
- the parsed shared `TrecQrels`;
- the metric and alternative used by every candidate comparison;
- the family-wise alpha;
- a tuple of `TrecCandidateComparison` records in candidate mapping order.

Each candidate record contains:

- the caller-provided candidate identifier;
- the complete parsed candidate `TrecRun`;
- the complete native `RankingComparisonReport`;
- the raw paired p-value;
- the Holm-adjusted p-value;
- the rejection decision at the requested family-wise alpha.

Run tags may be identical across baseline and candidates. A run tag is retained
provenance, not a unique candidate identity. The mapping key is the explicit
candidate identifier.

## Shared processing contract

The function parses the baseline and qrels once and evaluates the baseline once.
For each candidate it then:

1. parses the candidate run;
2. converts it to decreasing-score rankings;
3. evaluates it on the same qrels and cutoff;
4. compares it with the shared baseline evaluation through
   `compare_ranking_reports`;
5. retains the candidate artifact and complete paired evidence.

Candidate-specific failures are prefixed with the candidate identifier while
preserving the original parser, evaluation, or comparison message. Baseline and
qrels errors remain unchanged.

Every candidate receives the same explicit randomization seed. Monte Carlo
comparisons therefore use reproducible common sign streams. Holm's procedure
controls the family-wise error rate under arbitrary dependence, so shared
queries and correlated candidates do not invalidate the adjustment.

## Holm adjustment

For `m` raw p-values RankWeave:

1. sorts by raw p-value, breaking ties by candidate input order;
2. multiplies the p-value at sorted position `i` by `m - i`;
3. caps the result at one;
4. takes the cumulative maximum to enforce monotonic adjusted p-values;
5. maps adjusted values back to candidate input order.

A candidate is rejected when its adjusted p-value is less than or equal to
`familywise_alpha`.

For raw p-values `0.25`, `0.50`, and `1.00`, Holm-adjusted values are `0.75`,
`1.00`, and `1.00`. With alpha `0.80`, only the first candidate is rejected.

## Validation

The family comparison rejects:

- a non-mapping or empty candidate collection;
- duplicate or unhashable candidate identifiers from custom mappings;
- family-wise alpha outside `(0, 1]`, booleans, non-real values, or non-finite
  values;
- malformed baseline, candidate, or qrels artifacts;
- any candidate whose query set differs from the qrels query set;
- invalid cutoff, metric, alternative, randomization count, or seed.

Candidate order follows mapping insertion order and is preserved in the result,
even though Holm internally sorts p-values for adjustment.

## Interpretation boundary

Holm adjustment controls false rejections across the candidate family that the
caller supplied. Changing the family after seeing results changes the
statistical question. Define the candidate family before inspecting p-values.

Neither a raw nor adjusted p-value measures retrieval lift. Report the observed
mean difference and per-query evidence with the adjusted p-value. Statistical
significance does not establish practical importance, robustness to dataset
shift, operating cost, buyer value, or final held-out performance.

If candidate policies were selected on validation data, perform the family
comparison once on an independent held-out test set.

## Research grounding

Holm's sequentially rejective procedure controls the family-wise error rate for
arbitrarily dependent hypotheses and is uniformly at least as powerful as the
single-step Bonferroni procedure (Holm, 1979). Pairwise raw p-values use
RankWeave's Smucker-grounded paired randomization implementation. See
[Research grounding](research/README.md).

### Reference

Holm, S. (1979). A simple sequentially rejective multiple test procedure.
*Scandinavian Journal of Statistics, 6*(2), 65–70.
https://doi.org/10.2307/4615733

## Related documentation

- [Direct TREC run comparison](trec-run-comparison.md)
- [TREC interoperability](trec-interoperability.md)
- [Candidate-family design](superpowers/specs/2026-08-04-trec-family-comparison-design.md)
