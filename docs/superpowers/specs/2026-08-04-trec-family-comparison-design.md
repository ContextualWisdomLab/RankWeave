# TREC Candidate-Family Comparison Design

## Goal

Compare one baseline TREC run with a named family of candidate TREC runs, retain
every artifact and paired result, and control family-wise false positives with
Holm's sequentially rejective procedure.

## Buyer problem

Commercial retrieval evaluation rarely compares only one candidate with one
baseline. Teams test several fusion weights, embedding models, lexical
configurations, rerankers, and index variants. Running independent tests and
selecting the smallest p-value increases the chance of a false positive.
RankWeave currently makes each pairwise comparison auditable but does not
provide a safe, one-call family comparison or adjusted p-values.

## Public API

Create `src/rankweave/trec_family_comparison.py` with frozen records:

```python
@dataclass(frozen=True)
class TrecCandidateComparison:
    candidate_id: CandidateIdentifier
    candidate_run: TrecRun
    comparison: RankingComparisonReport[str]
    raw_p_value: float
    holm_adjusted_p_value: float
    rejected_at_familywise_alpha: bool


@dataclass(frozen=True)
class TrecRunFamilyComparisonReport:
    baseline_run: TrecRun
    qrels: TrecQrels
    metric_name: str
    alternative: str
    familywise_alpha: float
    candidates: tuple[TrecCandidateComparison, ...]


def compare_trec_run_family(
    baseline_run_text: str,
    candidate_run_texts: Mapping[CandidateIdentifier, str],
    qrels_text: str,
    *,
    cutoff: int,
    metric_name: str = NDCG_AT_K_METRIC,
    alternative: str = TWO_SIDED_ALTERNATIVE,
    familywise_alpha: float = 0.05,
    randomization_count: int = DEFAULT_RANDOMIZATION_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> TrecRunFamilyComparisonReport:
    ...
```

Candidate order follows mapping insertion order. Candidate identifiers are
retained exactly and must be unique and hashable.

## Processing

1. Parse the baseline run once.
2. Parse qrels once.
3. Evaluate the baseline once.
4. Snapshot the non-empty candidate mapping in insertion order.
5. Parse and evaluate each candidate against the same qrels and cutoff.
6. Compare each candidate report with the shared baseline report through
   `compare_ranking_reports`.
7. Apply Holm adjustment to the ordered family of raw p-values.
8. Return all candidate artifacts, raw and adjusted p-values, rejection flags,
   and paired evidence.

Candidate parser or query-set errors are prefixed with the candidate ID so a
large experiment identifies the failing artifact without losing the original
error.

## Holm adjustment

For `m` raw p-values:

1. sort ascending by raw p-value, breaking ties by candidate input order;
2. for sorted position `i` starting at zero, compute
   `(m - i) * p_i`, capped at one;
3. enforce monotonicity with the cumulative maximum;
4. map adjusted p-values back to candidate input order;
5. reject when adjusted p-value is at most `familywise_alpha`.

Holm's procedure controls the family-wise error rate under arbitrary dependence
and is uniformly at least as powerful as ordinary Bonferroni correction
(Holm, 1979).

## Validation

Fail closed unless:

- `candidate_run_texts` is a non-empty `Mapping`;
- candidate IDs are hashable and each candidate run text is valid;
- family-wise alpha is a finite real in `(0, 1]`, not a boolean;
- baseline, every candidate, and qrels contain exactly the same query IDs;
- cutoff, metric, alternative, randomization count, and seed satisfy existing
  comparison contracts.

Run tags are not candidate identifiers and may be repeated.

## Determinism

- baseline and qrels are parsed and evaluated once;
- candidate mapping order is preserved;
- ties in Holm ordering use candidate input order;
- every pairwise test receives the same explicit seed, producing a common,
  reproducible sign-randomization stream when Monte Carlo is needed;
- Holm remains valid under arbitrary dependence among pairwise p-values;
- global random state is untouched.

## Testing

Tests cover:

- three candidates with hand-checked raw p-values `0.25`, `0.5`, and `1.0` and
  Holm-adjusted values `0.75`, `1.0`, and `1.0`;
- family-wise alpha rejection flags;
- insertion order and tie ordering;
- identical run tags;
- malformed baseline, candidate, and qrels context;
- empty or non-mapping candidate collections;
- invalid alpha;
- exact and Monte Carlo pass-through;
- immutable public records;
- package exports, wheel content, installed-wheel smoke use;
- 100% production line and branch coverage and complete docstrings.

## Research grounding

Holm's step-down procedure supplies family-wise error control for any
configuration of true hypotheses (Holm, 1979). Pairwise p-values continue to
come from RankWeave's Smucker-grounded randomization test.

### Reference

Holm, S. (1979). A simple sequentially rejective multiple test procedure.
*Scandinavian Journal of Statistics, 6*(2), 65–70.
https://doi.org/10.2307/4615733

## Non-goals

No false-discovery-rate procedure, confidence interval, effect-size threshold,
model selection claim, automatic winner deployment, benchmark download, CLI,
or HTML dashboard is included.
