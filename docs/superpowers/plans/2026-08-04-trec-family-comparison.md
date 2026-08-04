# TREC Candidate-Family Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Compare one baseline TREC run with several named candidates and apply
Holm family-wise p-value correction while preserving every artifact and paired
result.

**Architecture:** Add one `trec_family_comparison.py` orchestration module. It
parses/evaluates the shared baseline and qrels once, delegates every candidate's
paired test to `compare_ranking_reports`, and owns only candidate-family
validation plus Holm adjustment.

**Tech Stack:** Python 3.10+, standard library, frozen dataclasses, pytest,
coverage, Ruff, Hatchling.

## Global Constraints

- No runtime dependencies.
- Python 3.10–3.13 compatibility.
- Store-agnostic and deterministic behavior.
- Frozen public audit records.
- 100% production line and branch coverage.
- Complete production docstrings.
- Package, documentation, version, and wheel smoke tests remain synchronized.

---

### Task 1: Write failing family-comparison tests

**Files:**
- Create: `tests/test_trec_family_comparison.py`

**Interfaces:**
- Expects `TrecCandidateComparison`, `TrecRunFamilyComparisonReport`, and
  `compare_trec_run_family`.

- [x] Pin three hand-checked raw p-values and their Holm-adjusted values.
- [x] Pin alpha rejection flags, insertion order, tie order, identical tags,
  exact and Monte Carlo pass-through, and immutability.
- [x] Pin empty/non-mapping candidates, invalid alpha, malformed artifact, and
  candidate-context errors.
- [x] Run the focused suite and observe the expected missing-module failure.
- [x] Commit the red tests.

### Task 2: Implement shared parsing, evaluation, and pairwise evidence

**Files:**
- Create: `src/rankweave/trec_family_comparison.py`
- Test: `tests/test_trec_family_comparison.py`

**Interfaces:**
- Produces the two frozen public records and `compare_trec_run_family`.
- Consumes `parse_trec_run`, `parse_trec_qrels`, `evaluate_rankings`, and
  `compare_ranking_reports`.

- [x] Validate and snapshot a non-empty candidate mapping.
- [x] Validate family-wise alpha in `(0, 1]`.
- [x] Parse baseline and qrels once and evaluate baseline once.
- [x] Parse each candidate, evaluate it, and compare it with the shared
  baseline report.
- [x] Prefix candidate-specific failures with the candidate identifier.
- [x] Run focused tests for artifact retention and validation.
- [x] Commit the orchestration layer.

### Task 3: Implement deterministic Holm adjustment

**Files:**
- Modify: `src/rankweave/trec_family_comparison.py`
- Test: `tests/test_trec_family_comparison.py`

**Interfaces:**
- Consumes each candidate's raw paired p-value.
- Produces adjusted p-values and rejection flags in candidate input order.

- [x] Sort by `(raw_p_value, input_index)`.
- [x] Compute capped step-down factors and cumulative maxima.
- [x] Map adjusted values back to input order.
- [x] Set `rejected_at_familywise_alpha` from adjusted values.
- [x] Run hand-checked, tie, and alpha tests.
- [x] Commit Holm correction.

### Task 4: Export, document, package, and release 0.9.0

**Files:**
- Modify: `src/rankweave/__init__.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/research/README.md`
- Create: `docs/trec-family-comparison.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_version.py`
- Create: `tests/test_trec_family_comparison_public_api.py`

**Interfaces:**
- Exposes family-comparison symbols from package root.
- Packages the new module and smoke-tests an installed wheel.

- [x] Document raw versus adjusted p-values and family definition.
- [x] Cite Holm (1979) in APA 7th edition and retain the practical-significance
  warning.
- [x] Update agent boundaries and package metadata.
- [x] Bump all release metadata to `0.9.0` together.
- [x] Run Ruff, full tests, 100% line/branch coverage, wheel verification,
  isolated installation, and `pip check` on the pre-rebase head.
- [ ] Rerun exact-head checks after rebasing onto current `main` and merge only
  after repository policy is satisfied.
