# Convex Score-Fusion Tuning Design

## Status

Approved for autonomous implementation under RankWeave's standing commercialization loop. This is one bounded public-API and release slice.

## Buyer-visible problem

RankWeave can fuse complete normalized-score lists with fixed convex weights and can tune weighted RRF policies, but it cannot select a scored-channel policy from judged validation queries. A lexical+dense buyer must currently reimplement the experiment loop, objective extraction, deterministic tie policy, and evidence retention outside RankWeave. That duplicates quality-sensitive code and breaks the closed experiment loop promised by the package.

Bruch, Gai, and Ingber (2024) report that convex score fusion can outperform RRF in both in-domain and out-of-domain settings and that its weight can be tuned sample-efficiently. A recent exhaustive Dutch hybrid-retrieval study also separates apparent same-sample optima from held-out selection and shows why fusion components must be justified by validation performance rather than standalone benchmark position (Barata, 2026, preprint). RankWeave should expose the auditable finite-policy selection primitive while leaving cross-validation split construction and final held-out testing to the caller.

## Considered approaches

### A. Continuous optimizer inside RankWeave

A continuous or Bayesian optimizer could search weights automatically, but it would add numerical dependencies, stopping criteria, optimizer state, and nondeterministic behavior. It would also hide which policies were actually evaluated. Rejected.

### B. Closed-form optimization of a retrieval metric

Ranked objectives such as nDCG, recall, precision, and reciprocal rank are discontinuous in the weights because document order changes at score crossings. A general closed-form optimum is not available. Rejected.

### C. Caller-defined finite convex-policy family

The caller supplies an ordered mapping of policy identifiers to convex channel weights. RankWeave fuses and evaluates every query for every policy, preserves the full immutable evidence, and selects the highest objective with first-policy tie breaking. This is deterministic, dependency-free, N-channel, and directly auditable. Recommended.

## Public API

Add to `rankweave.tuning` and the package root:

```python
@dataclass(frozen=True)
class WeightedConvexTuningTrial(Generic[PolicyIdentifier, QueryIdentifier]):
    policy_id: PolicyIdentifier
    channel_weights: tuple[tuple[str, float], ...]
    objective_score: float
    evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedConvexTuningReport(Generic[PolicyIdentifier, QueryIdentifier]):
    cutoff: int
    objective_name: str
    trials: tuple[
        WeightedConvexTuningTrial[PolicyIdentifier, QueryIdentifier], ...
    ]
    best_policy_id: PolicyIdentifier
    best_channel_weights: tuple[tuple[str, float], ...]
    best_objective_score: float


def tune_weighted_convex_fusion(
    channel_results_by_query: Mapping[
        QueryIdentifier,
        Mapping[str, Sequence[tuple[ItemIdentifier, float]]],
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    *,
    cutoff: int,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedConvexTuningReport[PolicyIdentifier, QueryIdentifier]:
    ...
```

## Processing contract

1. Validate `cutoff` as a positive integer.
2. Require one supported aggregate objective.
3. Require at least one candidate policy.
4. Validate that scored-query and judgment query identifiers match exactly and are non-empty before policy evaluation.
5. For each policy in insertion order:
   - delegate every query to `weighted_convex_fuse` with `limit=cutoff`;
   - delegate the resulting ranking map to `evaluate_rankings`;
   - retain the complete evaluation and an insertion-ordered immutable weight snapshot;
   - read the selected aggregate objective.
6. Select only on strictly greater objective score, so the first policy wins exact ties.
7. Return an immutable report containing every trial and the selected policy.

The function does not generate a grid, normalize raw provider scores, split queries, perform cross-validation, compare against the selected policy on the same data as if it were a final estimate, or deploy a policy.

## Validation and error boundaries

Existing delegated contracts remain authoritative:

- scores must be finite and in `[0, 1]`;
- channel weights must be finite, non-negative, and sum to one;
- a query result cannot contain a channel without a declared weight;
- duplicate or unhashable item identifiers fail closed;
- query and judgment sets must match exactly;
- unsupported objectives and empty policy families fail before partial reports are returned.

A weight may refer to a channel absent from one query; that query receives zero contribution for that channel, matching `weighted_convex_fuse`.

## Tests

Add focused tests for:

- selecting the lexical-heavy policy from scored evidence;
- retaining every aggregate and per-query evaluation;
- all supported objective paths;
- first-policy deterministic ties;
- query mismatch and empty query universe;
- empty policy family and unsupported objective;
- invalid cutoff;
- invalid convex weights;
- out-of-domain score, duplicate item, and undeclared result channel propagation;
- immutable trial and report records;
- package-root exports and version synchronization.

The normal Python 3.10–3.13 matrix, complete suite, 100% production statement/branch coverage, docstring checks, wheel/sdist inspection, and installed-wheel smoke remain merge gates.

## Documentation and release

Release as RankWeave `0.15.0`, an additive public feature. Synchronize:

- `pyproject.toml` and `uv.lock` local project version;
- `rankweave.__version__`;
- `tests/test_version.py`;
- package CI installed-wheel assertions;
- `README.md`, `docs/convex-fusion-tuning.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`, and `CHANGELOG.md`.

The documentation must distinguish validation-set policy selection from final held-out effectiveness and record the research sources in APA 7th edition.

## References — APA 7th edition

Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch retrieval? Cross-validated weighted RRF with paired inference and cross-domain transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for hybrid retrieval. *ACM Transactions on Information Systems, 42*(1), Article 20, 1–35. https://doi.org/10.1145/3596512
