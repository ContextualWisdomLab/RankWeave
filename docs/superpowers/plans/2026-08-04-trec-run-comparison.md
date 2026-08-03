# Direct TREC Run Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Turn three standard TREC text artifacts directly into one immutable,
auditable paired retrieval-system comparison.

**Architecture:** Add a thin `trec_comparison.py` orchestration module that
reuses strict TREC parsers and the existing native ranking comparison API.
Retain all parsed artifacts in the result rather than duplicating parsing,
evaluation, or randomization logic.

**Tech Stack:** Python 3.10+, standard library, frozen dataclasses, pytest,
coverage, Ruff, Hatchling.

## Global Constraints

- No runtime dependencies.
- Python 3.10–3.13 compatibility.
- Store-agnostic and deterministic behavior.
- Frozen public audit records.
- Existing parser, evaluation, and comparison errors propagate unchanged.
- 100% production line and branch coverage.
- Complete production docstrings.
- Release metadata, README, CHANGELOG, wheel contents, and smoke tests remain
  synchronized.

---

### Task 1: Define the artifact-to-comparison contract with failing tests

**Files:**
- Create: `tests/test_trec_comparison.py`

**Interfaces:**
- Produces expected imports:
  `TrecRunComparisonReport` and `compare_trec_runs`.

- [ ] Write an end-to-end test with two queries where score ordering makes the
  candidate better and assert the retained run tags, parsed artifacts, mean
  nDCG lift, method, and hand-computed one-sided exact p-value.
- [ ] Write tests for comments, identical run tags, immutable top-level result,
  baseline and candidate query-set mismatch, malformed artifacts, pass-through
  alternatives and metrics, Monte Carlo draw count and seed, and exact versus
  Monte Carlo selection.
- [ ] Run `pytest tests/test_trec_comparison.py -q` and confirm collection fails
  with `ModuleNotFoundError: No module named 'rankweave.trec_comparison'`.
- [ ] Commit the failing behavior tests.

### Task 2: Implement the thin TREC comparison orchestration

**Files:**
- Create: `src/rankweave/trec_comparison.py`
- Test: `tests/test_trec_comparison.py`

**Interfaces:**
- Produces frozen `TrecRunComparisonReport`.
- Produces `compare_trec_runs(...) -> TrecRunComparisonReport`.
- Consumes `parse_trec_run`, `parse_trec_qrels`, and `compare_rankings`.

- [ ] Define the frozen result with baseline run, candidate run, qrels, and
  native ranking comparison fields.
- [ ] Parse each text artifact exactly once.
- [ ] Convert runs to score-ordered mappings and qrels to non-negative generic
  judgments.
- [ ] Delegate all metric, cutoff, alternative, draw-count, seed, query-set,
  and significance behavior to `compare_rankings`.
- [ ] Return every parsed artifact and the comparison without mutation.
- [ ] Run focused tests and confirm they pass.
- [ ] Commit the production API.

### Task 3: Export and package the new API

**Files:**
- Modify: `src/rankweave/__init__.py`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_trec_comparison_public_api.py`

**Interfaces:**
- Exposes `TrecRunComparisonReport` and `compare_trec_runs` from package root.
- Packages `rankweave/trec_comparison.py` in the wheel.

- [ ] Add package-root imports and `__all__` entries.
- [ ] Add a package-root export contract test.
- [ ] Require the new module in wheel contents.
- [ ] Add an installed-wheel TREC comparison smoke assertion.
- [ ] Run focused export tests and the package job.
- [ ] Commit package integration.

### Task 4: Document and release RankWeave 0.8.0

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/research/README.md`
- Modify: `pyproject.toml`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`

**Interfaces:**
- Synchronizes package metadata and public version at `0.8.0`.

- [ ] Document the three-artifact workflow, preserved provenance, strict query
  parity, exact/Monte Carlo behavior, and identical-tag policy.
- [ ] Add the orchestration boundary and non-duplication rule to AGENTS.
- [ ] Cut a `0.8.0` CHANGELOG section.
- [ ] Keep the significance and TREC references explicit.
- [ ] Bump project metadata, public version, and expected-version test together.
- [ ] Run Ruff, complete pytest with 100% branch coverage, wheel build/content
  validation, isolated installation smoke test, and `pip check`.
- [ ] Open one PR, resolve actionable reviews, rerun exact-head checks, and
  squash merge only when repository policy is satisfied.
