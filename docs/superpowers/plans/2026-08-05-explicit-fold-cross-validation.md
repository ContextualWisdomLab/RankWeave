# Explicit-Fold Convex Fusion Cross-Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit blocked cross-validation for convex scored-channel policy selection and release it as RankWeave 0.16.0.

**Architecture:** Create a focused `cross_validation.py` orchestration module that delegates fold training to `tune_weighted_convex_fusion`, held-out fusion to `weighted_convex_fuse`, and all metrics to `evaluate_rankings`. The caller supplies exact fold assignments; RankWeave records them, evaluates the selection procedure out of fold, and returns a distinct full-data tuning recommendation.

**Tech Stack:** Python 3.10+, standard library only at runtime, pytest, Ruff, coverage.py, uv/hatchling packaging.

## Global Constraints

- Runtime remains dependency-free and Python 3.10+.
- Public behavior is additive and released as exactly `0.16.0`.
- No random folds, shuffling, hidden grouping, or random-number state.
- Scored, judgment, and fold-assignment query sets must match exactly and be non-empty.
- At least two distinct hashable fold identifiers are required.
- Query order comes from `channel_results_by_query`; fold order is first appearance in that query order.
- Every fold tunes only on the complement and evaluates only on its held-out queries.
- Out-of-fold evidence and full-data final tuning remain separate public fields.
- Existing convex-fusion score/weight validation and evaluation arithmetic remain authoritative.
- Production statement/branch coverage and public docstrings remain 100%.

---

### Task 1: Define failing explicit-fold behavior contracts

**Files:**
- Create: `tests/test_convex_cross_validation.py`

**Interfaces:**
- Consumes: future root exports `WeightedConvexCrossValidationFold`, `WeightedConvexCrossValidationReport`, and `cross_validate_weighted_convex_fusion`.
- Produces: complete membership, selection, evaluation, validation, order, and immutability contracts.

- [ ] **Step 1: Add a realistic blocked two-fold fixture**

Use four queries in deliberate non-fold-major order:

```python
scored_results = {
    "query-a1": {
        "lexical": [("a", 1.0), ("x", 0.0)],
        "dense": [("x", 1.0), ("a", 0.0)],
    },
    "query-b1": {
        "lexical": [("y", 1.0), ("b", 0.0)],
        "dense": [("b", 1.0), ("y", 0.0)],
    },
    "query-a2": {
        "lexical": [("c", 0.9), ("z", 0.1)],
        "dense": [("z", 0.9), ("c", 0.1)],
    },
    "query-b2": {
        "lexical": [("w", 0.9), ("d", 0.1)],
        "dense": [("d", 0.9), ("w", 0.1)],
    },
}
relevance = {
    "query-a1": {"a": 3},
    "query-b1": {"b": 3},
    "query-a2": {"c": 3},
    "query-b2": {"d": 3},
}
folds = {
    "query-a1": "a",
    "query-b1": "b",
    "query-a2": "a",
    "query-b2": "b",
}
```

This fixture makes fold `a` lexical-favoring and fold `b` dense-favoring, so training on the complement causes the two folds to select different fixed policies.

- [ ] **Step 2: Assert fold membership and out-of-fold behavior**

Require:

- fold order `a`, then `b` from first query appearance;
- fold `a` training queries `query-b1`, `query-b2` and held-out `query-a1`, `query-a2`;
- fold `b` training queries `query-a1`, `query-a2` and held-out `query-b1`, `query-b2`;
- fold `a` selects dense-heavy and fold `b` selects lexical-heavy;
- out-of-fold query metrics restore original query order;
- out-of-fold aggregate reflects applying each training-selected policy to its held-out fold;
- `final_tuning` is present and independent from fold held-out evaluations.

- [ ] **Step 3: Add deterministic objective and tie tests**

Parametrize all supported tuning objectives. Add identical policies and require the first policy to win in every fold and final tuning.

- [ ] **Step 4: Add validation tests**

Cover:

- fold-assignment query mismatch with both missing and extra assignments;
- zero and one distinct fold;
- unhashable fold ID;
- invalid cutoff values `0`, `1.5`, and `True`;
- unsupported objective;
- empty candidate family;
- non-convex weights;
- score outside `[0, 1]`;
- duplicate item identifier;
- result channel without a policy weight.

- [ ] **Step 5: Add immutable root-export tests**

Mutating fold/report fields must raise `FrozenInstanceError`, and the three public symbols must import from `rankweave`.

- [ ] **Step 6: Run focused tests and observe the red state**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_convex_cross_validation.py
```

Expected: collection FAIL because the new public module and symbols do not exist.

- [ ] **Step 7: Commit the red tests**

```bash
git add tests/test_convex_cross_validation.py
git commit -m "test(red): specify explicit-fold convex cross-validation"
```

### Task 2: Implement explicit-fold orchestration

**Files:**
- Create: `src/rankweave/cross_validation.py`
- Modify: `src/rankweave/__init__.py`
- Test: `tests/test_convex_cross_validation.py`
- Test: `tests/test_convex_tuning.py`

**Interfaces:**
- Consumes: `WeightedConvexTuningReport`, `tune_weighted_convex_fusion`, `weighted_convex_fuse`, `evaluate_rankings`, `_require_positive_integer`, and supported objective constants.
- Produces: `WeightedConvexCrossValidationFold`, `WeightedConvexCrossValidationReport`, and `cross_validate_weighted_convex_fusion`.

- [ ] **Step 1: Add generic identifiers and immutable records**

Implement the exact dataclasses from the design, with full public docstrings and no duplicated convenience fields that could contradict nested tuning/evaluation state.

- [ ] **Step 2: Validate the query and fold universe**

Create a private helper that:

```python
query_ids = tuple(channel_results_by_query)
result_query_set = set(query_ids)
judgment_query_set = set(relevance_by_query)
fold_query_set = set(fold_id_by_query)
```

Require the first two sets through `evaluate_rankings` with empty rankings, then compare fold assignments separately and report:

```text
fold assignments must match scored queries; missing assignments=[...], extra assignments=[...]
```

- [ ] **Step 3: Derive first-seen fold order with hashability validation**

```python
ordered_fold_ids = []
seen_fold_ids = set()
for query_id in query_ids:
    fold_id = fold_id_by_query[query_id]
    try:
        if fold_id not in seen_fold_ids:
            seen_fold_ids.add(fold_id)
            ordered_fold_ids.append(fold_id)
    except TypeError as exc:
        raise ValueError(
            f"fold identifier for query {query_id!r} must be hashable"
        ) from exc
if len(ordered_fold_ids) < 2:
    raise ValueError("cross-validation requires at least two distinct folds")
```

- [ ] **Step 4: Tune and evaluate each fold**

For each ordered fold:

- form training and held-out query tuples in original query order;
- build ordered subset dictionaries;
- call `tune_weighted_convex_fusion` on training data;
- convert `best_channel_weights` to one ordinary insertion-ordered dict;
- fuse held-out results with `weighted_convex_fuse(limit=cutoff)`;
- evaluate held-out rankings;
- store the fold report and rankings.

- [ ] **Step 5: Reassemble OOF evidence and final tuning**

Reorder held-out rankings to original `query_ids`, evaluate against all judgments, tune the full data, and return the immutable cross-validation report.

- [ ] **Step 6: Export the public symbols**

Add imports and `__all__` entries in `rankweave.__init__`.

- [ ] **Step 7: Run focused and tuning tests**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q \
  tests/test_convex_cross_validation.py tests/test_convex_tuning.py
```

Expected: PASS.

- [ ] **Step 8: Commit implementation**

```bash
git add src/rankweave/cross_validation.py src/rankweave/__init__.py \
  tests/test_convex_cross_validation.py tests/test_convex_tuning.py
git commit -m "feat: cross-validate convex fusion policies"
```

### Task 3: Document leakage-safe fold ownership

**Files:**
- Create: `docs/convex-fusion-cross-validation.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/research/README.md`

**Interfaces:**
- Consumes: the final API and Stone (1974), Cawley and Talbot (2010), Roberts et al. (2017), and Barata (2026).
- Produces: explicit fold examples, interpretation limits, structured-data guidance, and APA 7th references.

- [ ] **Step 1: Add a complete user example**

Show four query IDs, two explicit group/block fold IDs, a fixed policy family, fold-level selected policies, OOF evaluation, and final full-data policy recommendation.

- [ ] **Step 2: Document what each report means**

State:

- fold `tuning` uses no held-out judgments from that fold;
- fold `held_out_evaluation` assesses the selected procedure on that fold;
- `out_of_fold_evaluation` aggregates the procedure across all queries;
- `final_tuning` uses all judgments to recommend a future policy and is not a held-out estimate.

- [ ] **Step 3: Document grouped and temporal folds**

Require dependent query families to stay together when appropriate. Explicitly distinguish symmetric blocked folds from rolling-origin temporal evaluation.

- [ ] **Step 4: Synchronize architecture and contributor contracts**

Add `cross_validation.py` to the module map and prohibit random fold generation, hidden grouping, fusion duplication, or held-out/full-data interpretation collapse.

- [ ] **Step 5: Add APA 7th research references**

Add the four references from the design and explain why explicit caller-owned blocks are an API design choice rather than a claim that every supplied split is valid.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md ARCHITECTURE.md AGENTS.md CLAUDE.md \
  docs/convex-fusion-cross-validation.md docs/research/README.md
git commit -m "docs: explain blocked convex cross-validation"
```

### Task 4: Release RankWeave 0.16.0 and verify installed artifacts

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`
- Modify: `tests/test_verification_schema.py`
- Modify: `tests/test_verify_artifacts_cli.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/releasing.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: final public API and documentation.
- Produces: synchronized 0.16.0 metadata and installed-wheel cross-validation evidence.

- [ ] **Step 1: Synchronize version-bearing files**

Replace current active release assertions `0.15.0` with `0.16.0` in package metadata, local lock metadata, public version, version tests, installed-wheel assertions, README installation/current feature text, and release procedure. Do not rewrite historical 0.15.0 changelog or design records.

- [ ] **Step 2: Add the 0.16.0 changelog section**

Date it `2026-08-05` and record explicit caller-owned folds, fold-local tuning, OOF evaluation, final full-data recommendation, deterministic order, structured-data leakage guidance, and unchanged stdlib-only runtime.

- [ ] **Step 3: Extend wheel membership and installed smoke**

Require `rankweave/cross_validation.py` in the built wheel. From the installed wheel, import the three root symbols and execute a two-fold grouped case, asserting fold count, OOF query count, final policy, and record types.

- [ ] **Step 4: Run complete verification**

Run:

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: complete suite passes, production statement/branch coverage and public docstrings remain 100%, and wheel/sdist build. GitHub must then pass Python 3.10–3.13, package smoke, Security Scan, SAST Semgrep, current-head review, and zero unresolved threads.

- [ ] **Step 5: Commit release metadata**

```bash
git add pyproject.toml uv.lock src/rankweave/__init__.py \
  tests/test_version.py tests/test_verification_schema.py \
  tests/test_verify_artifacts_cli.py .github/workflows/ci.yml \
  README.md docs/releasing.md CHANGELOG.md
git commit -m "release: prepare RankWeave 0.16.0"
```

## Plan self-review

- **Spec coverage:** explicit folds, hashability, order, membership, fold-local selection, OOF reconstruction, final tuning, validation failures, exports, docs, research, release metadata, wheel contents, and installed smoke map to tasks.
- **Placeholder scan:** no TBD, TODO, deferred behavior, or unspecified validation remains.
- **Type consistency:** dataclass and function names/signatures match the design exactly.
- **Scope:** one blocked cross-validation vertical; no CLI, random folds, time-series rolling origin, database, network, LLM, UI, or adaptive per-query deployment.

## Execution mode

The standing commercialization loop selects inline execution with exact-head verification and review before merge.
