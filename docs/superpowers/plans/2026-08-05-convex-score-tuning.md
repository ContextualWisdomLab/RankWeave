# Convex Score-Fusion Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an auditable validation-set selector for fixed convex scored-channel fusion policies and release it as RankWeave 0.15.0.

**Architecture:** Extend the existing tuning module with immutable convex-policy trial/report records and a selector that composes `weighted_convex_fuse` with `evaluate_rankings`. Keep candidate generation, normalization, cross-validation splitting, and final held-out testing outside the function. Reuse existing objective constants and first-candidate deterministic tie behavior.

**Tech Stack:** Python 3.10+, standard library only at runtime, pytest, Ruff, coverage.py, uv/hatchling packaging.

## Global Constraints

- Runtime remains dependency-free and Python 3.10+.
- Public behavior is additive and released as exactly `0.15.0`.
- Input scores remain normalized finite values in `[0, 1]`.
- Channel weights remain finite, non-negative, insertion-ordered, and sum to one.
- Validation-query and judgment-query sets must match exactly and be non-empty.
- Candidate policy insertion order is the exact tie breaker.
- Every trial retains the complete immutable `RankingEvaluationReport`.
- Selection evidence is validation evidence, not final held-out performance.
- Production statement and branch coverage and public docstrings remain 100%.

---

### Task 1: Define the failing convex-tuning behavior contracts

**Files:**
- Create: `tests/test_convex_tuning.py`

**Interfaces:**
- Consumes: future root exports `WeightedConvexTuningReport`, `WeightedConvexTuningTrial`, and `tune_weighted_convex_fusion`.
- Produces: complete behavior, validation, immutability, and public-export contracts.

- [ ] **Step 1: Add scored fixtures and selection test**

```python
from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    WeightedConvexTuningReport,
    WeightedConvexTuningTrial,
    tune_weighted_convex_fusion,
)
from rankweave.evaluation import AggregateRankingMetrics


def _scored_results():
    return {
        "query-a": {
            "lexical": [("a", 1.0), ("b", 0.0)],
            "dense": [("b", 1.0), ("a", 0.0)],
        },
        "query-b": {
            "lexical": [("c", 0.9), ("d", 0.1)],
            "dense": [("d", 0.9), ("c", 0.1)],
        },
    }


def _judgments():
    return {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    }


def test_convex_tuning_selects_best_policy_by_mean_ndcg():
    report = tune_weighted_convex_fusion(
        _scored_results(),
        _judgments(),
        {
            "dense-heavy": {"lexical": 0.1, "dense": 0.9},
            "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
        },
        cutoff=1,
    )

    assert report.best_policy_id == "lexical-heavy"
    assert report.best_channel_weights == (("lexical", 0.9), ("dense", 0.1))
    assert report.best_objective_score == 1.0
    assert [trial.policy_id for trial in report.trials] == [
        "dense-heavy",
        "lexical-heavy",
    ]
    assert report.trials[1].evaluation.aggregate == AggregateRankingMetrics(
        query_count=2,
        mean_precision_at_k=1.0,
        mean_recall_at_k=1.0,
        mean_reciprocal_rank_at_k=1.0,
        mean_ndcg_at_k=1.0,
    )
```

- [ ] **Step 2: Add objective, deterministic tie, and immutable record tests**

Parametrize all four supported objective names. Add two identical policies and require the first policy to win. Mutating either record must raise `FrozenInstanceError`.

- [ ] **Step 3: Add fail-closed validation tests**

Cover unsupported objective, empty candidate family, query-set mismatch, empty query set, invalid cutoff values `0`, `1.5`, and `True`, non-convex weights, score `1.1`, duplicate item identifiers, and an input channel missing from a policy.

- [ ] **Step 4: Run the focused tests and observe the red state**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_convex_tuning.py
```

Expected: collection FAIL because the three public symbols do not exist.

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/test_convex_tuning.py
git commit -m "test(red): specify convex score-fusion tuning"
```

### Task 2: Implement immutable convex-policy selection

**Files:**
- Modify: `src/rankweave/tuning.py`
- Modify: `src/rankweave/__init__.py`
- Test: `tests/test_convex_tuning.py`
- Test: `tests/test_tuning.py`

**Interfaces:**
- Consumes: `weighted_convex_fuse`, `evaluate_rankings`, existing objective constants, and existing validation contracts.
- Produces: `WeightedConvexTuningTrial`, `WeightedConvexTuningReport`, and `tune_weighted_convex_fusion`.

- [ ] **Step 1: Import the scored fusion primitive**

```python
from rankweave.ranked_list_fusion import (
    weighted_convex_fuse,
    weighted_reciprocal_rank_fuse,
)
```

- [ ] **Step 2: Add the immutable records**

Implement the exact generic dataclasses from the design. Do not add mutable derived fields or post-construction mutation.

- [ ] **Step 3: Implement the selector**

Use this processing skeleton:

```python
validated_cutoff = _require_positive_integer(cutoff, "cutoff")
if objective_name not in SUPPORTED_TUNING_OBJECTIVES:
    raise ValueError(...)
if not candidate_channel_weights:
    raise ValueError("tuning requires at least one candidate policy")

evaluate_rankings(
    {query_id: () for query_id in channel_results_by_query},
    relevance_by_query,
    cutoff=validated_cutoff,
)

trials = []
for policy_id, channel_weights in candidate_channel_weights.items():
    fused_rankings_by_query = {
        query_id: tuple(
            fused_item.item_id
            for fused_item in weighted_convex_fuse(
                channel_results,
                channel_weights,
                limit=validated_cutoff,
            )
        )
        for query_id, channel_results in channel_results_by_query.items()
    }
    evaluation = evaluate_rankings(
        fused_rankings_by_query,
        relevance_by_query,
        cutoff=validated_cutoff,
    )
    objective_score = getattr(evaluation.aggregate, objective_name)
    trials.append(...)
```

Select only on `>` to preserve first-policy ties, then return the immutable report.

- [ ] **Step 4: Export the symbols**

Add all three symbols to package imports and `__all__`, maintaining alphabetical grouping where practical.

- [ ] **Step 5: Run focused and existing tuning tests**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest -q tests/test_convex_tuning.py tests/test_tuning.py
```

Expected: PASS.

- [ ] **Step 6: Commit the implementation**

```bash
git add src/rankweave/tuning.py src/rankweave/__init__.py \
  tests/test_convex_tuning.py tests/test_tuning.py
git commit -m "feat: tune convex score-fusion policies"
```

### Task 3: Document the scientific and operational boundary

**Files:**
- Create: `docs/convex-fusion-tuning.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/research/README.md`

**Interfaces:**
- Consumes: the final API and the Bruch et al. (2024) and Barata (2026) evidence.
- Produces: standalone/MSA usage examples, interpretation boundaries, and APA 7th references.

- [ ] **Step 1: Write the user workflow**

Document one complete lexical+dense validation example, report fields, objective choices, first-policy tie handling, invalid-input behavior, and naruon/MSA import suitability.

- [ ] **Step 2: State the inference boundary**

State explicitly that the caller defines the policy family before inspecting validation results and evaluates the selected policy once on an independent held-out test set. Same-sample selection and reporting is an optimistic estimate.

- [ ] **Step 3: Synchronize architecture and agent contracts**

Add convex policy tuning to the module map and require delegation to `weighted_convex_fuse` and `evaluate_rankings`; prohibit duplicate fusion or metric arithmetic in `tuning.py`.

- [ ] **Step 4: Add APA 7th research grounding**

Record:

```text
Barata, A. P. (2026). Do static embeddings add value to hybrid Dutch
retrieval? Cross-validated weighted RRF with paired inference and cross-domain
transfer [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for
hybrid retrieval. ACM Transactions on Information Systems, 42(1), Article 20,
1–35. https://doi.org/10.1145/3596512
```

- [ ] **Step 5: Commit documentation**

```bash
git add README.md ARCHITECTURE.md AGENTS.md CLAUDE.md \
  docs/convex-fusion-tuning.md docs/research/README.md
git commit -m "docs: explain convex fusion policy selection"
```

### Task 4: Release RankWeave 0.15.0 and verify installed artifacts

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: final public API and documentation.
- Produces: synchronized 0.15.0 package metadata and installed-wheel evidence.

- [ ] **Step 1: Synchronize version-bearing files**

Replace the local project version `0.14.0` with `0.15.0` in package metadata, lock metadata, public version, version test, and installed-wheel assertions. Do not alter historical documentation that intentionally describes 0.14.0.

- [ ] **Step 2: Add the 0.15.0 changelog section**

Date it `2026-08-05`. Record the public selector, immutable reports, complete evidence, deterministic ties, validation/test separation, and unchanged stdlib-only runtime.

- [ ] **Step 3: Extend installed-wheel smoke**

Import the three new root symbols from the installed wheel and run a minimal two-query convex tuning case that selects the expected policy.

- [ ] **Step 4: Run the complete exact-head gate**

Run:

```bash
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Expected: complete tests pass, production statement and branch coverage remain 100%, production docstrings remain complete, and wheel/sdist build. GitHub must then pass Python 3.10–3.13, package smoke, Security Scan, and SAST Semgrep at the exact PR head.

- [ ] **Step 5: Commit the release metadata**

```bash
git add pyproject.toml uv.lock src/rankweave/__init__.py \
  tests/test_version.py .github/workflows/ci.yml CHANGELOG.md
git commit -m "release: prepare RankWeave 0.15.0"
```

## Plan self-review

- **Spec coverage:** public records, selector, all validation branches, full evidence, deterministic ties, root exports, docs, research, release metadata, and installed-wheel smoke map to tasks.
- **Placeholder scan:** no TBD, TODO, deferred behavior, or unspecified validation remains.
- **Type consistency:** signatures and record fields match the design exactly.
- **Scope:** one scored-fusion policy-selection vertical; no CLI, database, network, LLM runtime, UI, or adaptive per-query weighting.

## Execution mode

The standing commercialization loop selects inline execution with exact-head verification and review before merge.
