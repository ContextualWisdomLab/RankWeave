# Weighted-RRF Cross-Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic explicit-fold cross-validation for fixed weighted-RRF policies while preserving complete training and held-out evaluation evidence.

**Architecture:** Keep convex and RRF public APIs explicit. Extract only strategy-neutral request validation into private helpers in `cross_validation.py`; the new RRF path delegates policy selection to `tune_weighted_reciprocal_rank_fusion`, rank fusion to `weighted_reciprocal_rank_fuse`, and metrics to `evaluate_rankings`.

**Tech Stack:** Python 3.10+, standard library, pytest, coverage.py, Ruff, Hatchling, uv, GitHub Actions.

## Global Constraints

- Runtime remains Python 3.10+ and standard-library-only.
- Public convex cross-validation behavior and type names remain unchanged.
- `rank_constant_eta` is one positive integer shared by every fold and final tuning.
- Candidate and fold insertion order are audit evidence and deterministic tie breakers.
- Query and judgment universes must match exactly; omitted queries never inflate metrics.
- Production statement coverage, branch coverage, and public docstrings remain 100%.
- Release metadata, wheel smoke, `uv.lock`, documentation, and `CHANGELOG.md` synchronize at 0.18.0.
- No database, network, UI, LLM, scheduler, central workflow, or credential changes.

---

### Task 1: Add failing weighted-RRF fold behavior contracts

**Files:**
- Create: `tests/test_rrf_cross_validation.py`
- Read: `src/rankweave/cross_validation.py`
- Read: `src/rankweave/tuning.py`

**Interfaces:**
- Consumes: `cross_validate_weighted_reciprocal_rank_fusion`, `WeightedRRFCrossValidationFold`, and `WeightedRRFCrossValidationReport` from the package root.
- Produces: executable requirements for selection, fixed eta, fold ordering, full evaluations, validation, and immutability.

- [ ] **Step 1: Write a four-query two-fold selection test**

Use lexical and dense rank-only channels so one complementary training fold selects `dense-heavy` and the other selects `lexical-heavy`. Assert fold ID order, exact training and held-out query IDs, selected policy IDs, held-out nDCG, original query-order out-of-fold metrics, final tuning, and `rank_constant_eta`.

- [ ] **Step 2: Add validation tests**

Cover every tuning objective, first-policy exact ties, missing/extra fold assignments, fewer than two folds, unhashable fold IDs, invalid cutoff, invalid eta values `0`, `1.5`, and `True`, unsupported objective, empty policy family, non-convex weights, duplicate item identifiers, unhashable item identifiers, and ranking channels without weights.

- [ ] **Step 3: Add immutable-record tests**

Assert the returned fold and report use the new frozen record types and reject field assignment with `FrozenInstanceError`.

- [ ] **Step 4: Run the focused test and observe red**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_rrf_cross_validation.py
```

Expected: collection fails because the new root symbols do not exist.

- [ ] **Step 5: Commit the red contract**

```bash
git add tests/test_rrf_cross_validation.py
git commit -m "test(red): specify weighted-RRF cross-validation"
```

### Task 2: Share request validation without changing convex behavior

**Files:**
- Modify: `src/rankweave/cross_validation.py`
- Test: `tests/test_convex_cross_validation.py`
- Test: `tests/test_rrf_cross_validation.py`

**Interfaces:**
- Produces: private `_validate_cross_validation_request(...)` returning `(validated_cutoff, query_ids, fold_ids)`.
- Preserves: `cross_validate_weighted_convex_fusion(...)` signature and output.

- [ ] **Step 1: Extract the shared validator**

Implement a private helper that validates cutoff, objective, non-empty candidate policy family, exact query/judgment parity through `evaluate_rankings`, exact fold assignments, hashable fold identifiers, and at least two distinct folds.

- [ ] **Step 2: Route convex cross-validation through the helper**

Remove duplicated validation from `cross_validate_weighted_convex_fusion` and consume the helper result. Do not change fold order, training/held-out membership, fusion, metrics, tie handling, or final tuning.

- [ ] **Step 3: Run the existing convex suite**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_convex_cross_validation.py
```

Expected: all existing tests pass unchanged.

- [ ] **Step 4: Commit the refactor**

```bash
git add src/rankweave/cross_validation.py tests/test_convex_cross_validation.py
git commit -m "refactor: share cross-validation request checks"
```

### Task 3: Implement weighted-RRF explicit-fold cross-validation

**Files:**
- Modify: `src/rankweave/cross_validation.py`
- Modify: `src/rankweave/__init__.py`
- Test: `tests/test_rrf_cross_validation.py`

**Interfaces:**
- Produces:
  - `WeightedRRFCrossValidationFold`
  - `WeightedRRFCrossValidationReport`
  - `cross_validate_weighted_reciprocal_rank_fusion(...)`

- [ ] **Step 1: Add frozen RRF records**

The fold stores `fold_id`, `training_query_ids`, `held_out_query_ids`, the complete `WeightedRRFTuningReport`, and the complete held-out `RankingEvaluationReport`. The report stores `cutoff`, `rank_constant_eta`, `objective_name`, all folds, the aggregate out-of-fold evaluation, and full-data final tuning.

- [ ] **Step 2: Implement the RRF orchestration**

Validate the positive eta with `_require_positive_integer`. For each fold, tune only on complementary training queries, convert the selected ordered weights to a mapping, apply `weighted_reciprocal_rank_fuse` with the same eta and cutoff to every held-out query, evaluate the fold, reconstruct all out-of-fold rankings in original query order, and run final full-data tuning with the same eta.

- [ ] **Step 3: Export the new symbols**

Import and include all three new public symbols in `rankweave.__all__`.

- [ ] **Step 4: Run focused convex and RRF tests**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q \
  tests/test_convex_cross_validation.py \
  tests/test_rrf_cross_validation.py
```

Expected: both suites pass.

- [ ] **Step 5: Commit the feature**

```bash
git add src/rankweave/cross_validation.py src/rankweave/__init__.py \
  tests/test_rrf_cross_validation.py
git commit -m "feat: cross-validate weighted-RRF policies"
```

### Task 4: Synchronize RankWeave 0.18.0 and installed-package evidence

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`
- Modify: `tests/test_verification_schema.py`
- Modify: `tests/test_verify_artifacts_cli.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/publish.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: one synchronized 0.18.0 release and installed-wheel proof of the new API.

- [ ] **Step 1: Update every version-bearing file**

Replace the local project version, public version, expected version tests, schema fixture version, CLI verification expectations, README/release examples that name the current package version, and local `uv.lock` project stanza with `0.18.0`.

- [ ] **Step 2: Expand wheel and release archive inspection**

Keep `rankweave/cross_validation.py` required in both CI and publication workflows. Add an installed-wheel rank-only two-fold cross-validation smoke that asserts the new report and fold types, fixed eta, two folds, and original aggregate query count.

- [ ] **Step 3: Add the changelog release section**

Document public API, fixed-eta validation, blocked-fold interpretation, standard-library compatibility, and the requirement for an independent final test set.

- [ ] **Step 4: Run version and package-focused tests**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q \
  tests/test_version.py \
  tests/test_verification_schema.py \
  tests/test_verify_artifacts_cli.py \
  tests/test_rrf_cross_validation.py
```

Expected: all pass.

- [ ] **Step 5: Commit release integration**

```bash
git add pyproject.toml uv.lock src/rankweave/__init__.py \
  tests/test_version.py tests/test_verification_schema.py \
  tests/test_verify_artifacts_cli.py .github/workflows/ci.yml \
  .github/workflows/publish.yml CHANGELOG.md
git commit -m "release: prepare RankWeave 0.18.0"
```

### Task 5: Document scientific and modular operating boundaries

**Files:**
- Create: `docs/rrf-cross-validation.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/research/README.md`
- Modify: `docs/releasing.md`

**Interfaces:**
- Produces: operator-facing API examples, a Mermaid data-flow diagram, APA 7th references, and maintained agent/release rules.

- [ ] **Step 1: Write the operator document**

Document inputs, a complete example, fold ownership, fixed eta, retained evidence, missing-rank semantics, blocked-fold guidance, final-tuning separation, scope limits, and APA 7th references.

- [ ] **Step 2: Update product and architecture docs**

Add a README example and link. Add the new rank-only cross-validation flow to the module map and policy-selection boundary. State in `AGENTS.md` and `CLAUDE.md` that RRF cross-validation must delegate to native RRF tuning/fusion, preserve eta, and keep all-data tuning distinct from held-out evidence.

- [ ] **Step 3: Update research and release guidance**

Record Cormack et al. (2009), Samuel et al. (2025), Stone (1974), Cawley and Talbot (2010), and Roberts et al. (2017) in APA 7th form or link to existing complete entries without duplicating contradictory metadata. Update release verification examples to 0.18.0.

- [ ] **Step 4: Commit documentation**

```bash
git add docs/rrf-cross-validation.md README.md ARCHITECTURE.md \
  AGENTS.md CLAUDE.md docs/research/README.md docs/releasing.md
git commit -m "docs: explain blocked weighted-RRF assessment"
```

### Task 6: Verify the exact head and prepare protected merge

**Files:**
- Verify all changed files.

**Interfaces:**
- Produces: exact-head evidence suitable for current-head review and protected merge.

- [ ] **Step 1: Run complete local verification**

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: all tests pass; production statement and branch coverage are 100%; both archives build.

- [ ] **Step 2: Confirm the final diff boundary**

Reject any workflow, credential, database, UI, LLM, scheduler, provider, runtime dependency, or unrelated refactor change.

- [ ] **Step 3: Open or update the PR as ready**

Describe the buyer outcome, public contract, blocked-fold boundary, exact-head evidence, 0.18.0 release scope, modularity, and interpretation limits.

- [ ] **Step 4: Revalidate hosted gates**

Require Python 3.10–3.13 CI, package smoke, Security Scan, SAST Semgrep, current-head review, and zero unresolved threads before squash merge.

## Plan self-review

- **Spec coverage:** API, fixed eta, blocked folds, shared validation, native delegation, evidence, release, docs, and hosted gates each map to a task.
- **Placeholder scan:** no TODO, TBD, “similar to,” or unspecified implementation remains.
- **Type consistency:** public names and signatures are identical across spec, tasks, tests, exports, and docs.
- **Scope:** temporal RRF backtesting, transport schemas, CLI, adaptive routing, and deployment are excluded from this release.

## Execution mode

The standing commercialization instruction selects inline execution with exact-head checkpoints and protected merge.
