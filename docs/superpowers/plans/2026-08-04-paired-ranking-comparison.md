# Paired Ranking Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add fail-closed paired randomization comparison for two retrieval
systems evaluated on the same query set.

**Architecture:** Keep ranking evaluation in `evaluation.py`; add one focused
`comparison.py` module for report validation, query alignment, paired
differences, exact sign enumeration, and deterministic Monte Carlo sampling.
Expose immutable result records and an end-to-end convenience function.

**Tech Stack:** Python 3.10+, standard library, dataclasses, `random.Random`,
pytest, coverage, Ruff, Hatchling.

## Global Constraints

- No runtime dependencies.
- Python 3.10–3.13 compatibility.
- Store-agnostic and deterministic behavior.
- Frozen public audit records.
- Fail-closed input contracts.
- 100% production line and branch coverage.
- Complete production docstrings.
- Release metadata, README, CHANGELOG, wheel contents, and smoke tests remain
  synchronized.

---

### Task 1: Define the paired-comparison behavior with failing tests

**Files:**
- Create: `tests/test_comparison.py`

**Interfaces:**
- Produces expected imports:
  `compare_ranking_reports`, `compare_rankings`,
  `QueryMetricDifference`, `PairedRandomizationResult`, and
  `RankingComparisonReport`.

- [ ] Write a test with two two-query reports whose per-query differences are
  `(+1, -0.5)` and assert the exact two-sided p-value is `1.0`.
- [ ] Write one-sided tests that assert `candidate-greater` and
  `candidate-less` count the correct sign assignments.
- [ ] Write a query-order test where candidate query metrics are reversed but
  alignment still follows query ID.
- [ ] Write all-zero, exact-boundary, Monte Carlo determinism, immutability, and
  end-to-end `compare_rankings` tests.
- [ ] Write validation tests for unsupported metric/alternative, mismatched
  cutoff/query sets, duplicate or unhashable query IDs, invalid metric values,
  invalid seeds, and invalid draw counts.
- [ ] Run `pytest tests/test_comparison.py -q` and confirm collection fails with
  `ModuleNotFoundError: No module named 'rankweave.comparison'`.
- [ ] Commit the failing behavioral tests.

### Task 2: Implement immutable comparison records and validation

**Files:**
- Create: `src/rankweave/comparison.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Produces constants for supported metrics, alternatives, and methods.
- Produces frozen `QueryMetricDifference`, `PairedRandomizationResult`, and
  `RankingComparisonReport` dataclasses.

- [ ] Add whitelists for `precision_at_k`, `recall_at_k`,
  `reciprocal_rank_at_k`, and `ndcg_at_k`.
- [ ] Add `two-sided`, `candidate-greater`, and `candidate-less` alternatives.
- [ ] Validate report type, cutoff, non-empty metrics, aggregate query count,
  metric cutoff, unique hashable query IDs, selected metric domain, query-set
  parity, seed, and draw count.
- [ ] Align candidate values by query ID while retaining baseline order.
- [ ] Run focused validation tests and confirm they pass.
- [ ] Commit the records and validation layer.

### Task 3: Implement exact and deterministic Monte Carlo randomization

**Files:**
- Modify: `src/rankweave/comparison.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Produces `compare_ranking_reports(...) -> PairedRandomizationResult`.

- [ ] Compute candidate-minus-baseline differences and observed signed sum.
- [ ] Enumerate all sign assignments for at most 16 non-zero pairs.
- [ ] Use local `random.Random(random_seed)` sign draws above 16 pairs.
- [ ] Apply the exact and plus-one Monte Carlo p-value formulas.
- [ ] Implement two-sided and candidate-directed extreme-statistic predicates
  with a `1e-15` tolerance.
- [ ] Return complete immutable per-query evidence.
- [ ] Run all focused tests and confirm both exact and Monte Carlo paths pass.
- [ ] Commit the paired randomization implementation.

### Task 4: Add the end-to-end ranking comparison API

**Files:**
- Modify: `src/rankweave/comparison.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Produces `compare_rankings(...) -> RankingComparisonReport`.
- Consumes `evaluate_rankings(...) -> RankingEvaluationReport`.

- [ ] Evaluate baseline and candidate ranking maps against the same relevance
  mapping and cutoff.
- [ ] Compare the resulting reports through `compare_ranking_reports`.
- [ ] Preserve both evaluation reports and the significance result.
- [ ] Run focused end-to-end tests.
- [ ] Commit the convenience API.

### Task 5: Export, package, document, and release 0.7.0

**Files:**
- Modify: `src/rankweave/__init__.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Modify: `tests/test_version.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/research/README.md`

**Interfaces:**
- Exposes all comparison symbols from package root.
- Packages `rankweave/comparison.py` in the wheel.

- [ ] Add package-root exports and an installed-wheel smoke comparison.
- [ ] Assert `rankweave/comparison.py` exists in the built wheel.
- [ ] Document statistical and practical interpretation, exact versus Monte
  Carlo behavior, validation/test separation, and the primary citation.
- [ ] Bump project metadata, public version, expected-version test, and
  CHANGELOG to `0.7.0` together.
- [ ] Run Ruff, full pytest with 100% branch coverage, wheel build/content
  validation, isolated install smoke test, and `pip check`.
- [ ] Open one PR, resolve actionable reviews, rerun exact-head checks, and
  squash merge only after repository policy is satisfied.
