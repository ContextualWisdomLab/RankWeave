"""Apply the reviewed RankWeave 0.15.0 convex-tuning release edits."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path_text: str) -> str:
    return (ROOT / path_text).read_text(encoding="utf-8")


def _write(path_text: str, content: str) -> None:
    (ROOT / path_text).write_text(content, encoding="utf-8")


def _replace_once(path_text: str, old: str, new: str) -> None:
    content = _read(path_text)
    count = content.count(old)
    if count != 1:
        raise SystemExit(
            f"{path_text}: expected one replacement target, found {count}"
        )
    _write(path_text, content.replace(old, new, 1))


def _replace_all(path_text: str, old: str, new: str) -> None:
    content = _read(path_text)
    count = content.count(old)
    if count < 1:
        raise SystemExit(f"{path_text}: replacement target is absent")
    _write(path_text, content.replace(old, new))


def _insert_before(path_text: str, marker: str, addition: str) -> None:
    content = _read(path_text)
    if addition.strip() in content:
        return
    count = content.count(marker)
    if count != 1:
        raise SystemExit(
            f"{path_text}: expected one insertion marker, found {count}"
        )
    _write(path_text, content.replace(marker, addition + marker, 1))


for version_path in (
    "pyproject.toml",
    "src/rankweave/__init__.py",
    "tests/test_version.py",
    "tests/test_verification_schema.py",
    "tests/test_verify_artifacts_cli.py",
    ".github/workflows/ci.yml",
    "README.md",
    "docs/releasing.md",
):
    _replace_all(version_path, "0.14.0", "0.15.0")

README_SECTION = """## Tune a fixed convex score-fusion policy

```python
from rankweave import tune_weighted_convex_fusion

report = tune_weighted_convex_fusion(
    {
        "query-a": {
            "lexical": [("a", 1.0), ("b", 0.0)],
            "dense": [("b", 1.0), ("a", 0.0)],
        },
        "query-b": {
            "lexical": [("c", 0.9), ("d", 0.1)],
            "dense": [("d", 0.9), ("c", 0.1)],
        },
    },
    {
        "query-a": {"a": 3},
        "query-b": {"c": 3},
    },
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    cutoff=1,
)

assert report.best_policy_id == "lexical-heavy"
```

The caller defines the finite policy family before inspecting validation
results. Every trial retains its complete immutable evaluation, and the first
policy wins an exact objective tie. Freeze the selected weights and evaluate
them once on an independent held-out test set before reporting final quality.

See [Convex score-fusion policy tuning](docs/convex-fusion-tuning.md).

"""
_insert_before(
    "README.md",
    "## Tune a fixed weighted-RRF policy\n",
    README_SECTION,
)

_replace_once(
    "ARCHITECTURE.md",
    "- `tuning.py` — validation-set weighted-RRF policy selection.\n",
    "- `tuning.py` — validation-set convex-score and weighted-RRF policy "
    "selection.\n",
)
_insert_before(
    "ARCHITECTURE.md",
    "## Compatibility and release policy\n",
    """## Offline policy-selection boundary

`tuning.py` defines deterministic experiment orchestration, not a second fusion
or metric engine. Convex score policies delegate to `weighted_convex_fuse`;
weighted-RRF policies delegate to `weighted_reciprocal_rank_fuse`; both delegate
all effectiveness calculation to `evaluate_rankings`. Candidate insertion order
is preserved as the exact tie breaker, and every trial retains its complete
immutable evaluation. Grid generation, score normalization, validation splits,
cross-validation, and final held-out inference remain caller responsibilities.

""",
)

AGENT_MARKER = """- **Deterministic model selection.** Candidate mapping insertion order is the
  tie-breaker for equal objective values. Do not replace it with unordered set
  iteration or nondeterministic reduction.
"""
AGENT_REPLACEMENT = AGENT_MARKER + """- **Convex tuning delegates rather than duplicates.** Scored-policy selection
  must call `weighted_convex_fuse` and `evaluate_rankings`, retain every full
  immutable evaluation, and treat the supplied policy order as audit evidence.
  Do not normalize provider scores, generate a hidden search space, or present
  validation selection as held-out effectiveness.
"""
_replace_once("AGENTS.md", AGENT_MARKER, AGENT_REPLACEMENT)

_insert_before(
    "CLAUDE.md",
    "## Artifact verification\n",
    """## Convex score-fusion tuning

Keep scored-policy selection as deterministic composition of
`weighted_convex_fuse` and `evaluate_rankings`. Preserve every trial, caller
weight order, exact first-policy ties, query-set parity, and the independent
held-out-test boundary. Do not add a runtime optimizer or numerical dependency.

""",
)

OLD_TUNING_RESEARCH = """## Tuning protocol

`tune_weighted_reciprocal_rank_fusion` evaluates named fixed-weight policies on
a complete judged validation query set. It supports macro nDCG, reciprocal
rank, recall, or precision and preserves candidate insertion order as the exact
tie-breaker.

The selected validation policy is not an unbiased final effectiveness estimate.
Consumers must evaluate it once on an independent held-out test set before
making a production-quality claim.

"""
NEW_TUNING_RESEARCH = """## Tuning protocol

`tune_weighted_convex_fusion` and `tune_weighted_reciprocal_rank_fusion`
evaluate caller-defined, insertion-ordered fixed-weight policy families on a
complete judged validation query set. Both support macro nDCG, reciprocal rank,
recall, or precision, preserve every full evaluation, and use candidate order as
the exact tie breaker.

Bruch et al. (2024) report that convex combination can outperform RRF in- and
out-of-domain and can be tuned sample-efficiently. Barata (2026, preprint)
illustrates the stricter experiment boundary adopted here: select a finite
simplex policy only on training queries, distinguish the apparent full-data
optimum from out-of-fold performance, and test marginal fusion value rather than
assuming that a standalone retriever must help a hybrid.

The selected validation policy is not an unbiased final effectiveness estimate.
Consumers must freeze the chosen weights and evaluate them once on an
independent held-out test set before making a production-quality claim.

"""
_replace_once(
    "docs/research/README.md",
    OLD_TUNING_RESEARCH,
    NEW_TUNING_RESEARCH,
)
_insert_before(
    "docs/research/README.md",
    "Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions",
    """Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch
retrieval? Cross-validated weighted RRF with paired inference and cross-domain
transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

""",
)

CHANGELOG_ENTRY = """## [0.15.0] - 2026-08-05

### Added
- Public `WeightedConvexTuningTrial`, `WeightedConvexTuningReport`, and
  `tune_weighted_convex_fusion` APIs for deterministic selection among fixed
  convex scored-channel policies.
- Complete immutable per-policy evaluation evidence, objective selection across
  nDCG, reciprocal rank, recall, and precision, and first-policy exact-tie
  behavior.
- Dedicated scored-fusion tuning documentation, architecture and agent
  contracts, package-root exports, installed-wheel smoke, and research grounding
  in Bruch et al. (2024) plus a clearly identified 2026 preprint on held-out
  fusion selection.

### Validation
- Scored-query and judgment sets must match exactly; policy weights, normalized
  scores, duplicate items, undeclared channels, objectives, and cutoff values
  fail closed through the existing fusion and evaluation contracts.
- Selection remains a validation-set operation. Final effectiveness requires an
  independent held-out test set; RankWeave does not generate a hidden search
  grid, normalize provider scores, or deploy the selected policy.

### Compatibility
- Runtime remains standard-library-only, Python 3.10+, store-agnostic,
  standalone-usable, and suitable for naruon or another MSA consumer.

"""
_insert_before(
    "CHANGELOG.md",
    "## [0.14.0] — 2026-08-05\n",
    CHANGELOG_ENTRY,
)

CI_SMOKE_MARKER = """          assert verification.verified is True
          assert verification.mismatch_count == 0
          PY
"""
CI_SMOKE_REPLACEMENT = """          assert verification.verified is True
          assert verification.mismatch_count == 0

          tuning = rankweave.tune_weighted_convex_fusion(
              {
                  "q1": {
                      "lexical": [("a", 1.0), ("b", 0.0)],
                      "dense": [("b", 1.0), ("a", 0.0)],
                  },
                  "q2": {
                      "lexical": [("c", 0.9), ("d", 0.1)],
                      "dense": [("d", 0.9), ("c", 0.1)],
                  },
              },
              {"q1": {"a": 1}, "q2": {"c": 1}},
              {
                  "dense-heavy": {"lexical": 0.1, "dense": 0.9},
                  "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
              },
              cutoff=1,
          )
          assert tuning.best_policy_id == "lexical-heavy"
          assert isinstance(tuning, rankweave.WeightedConvexTuningReport)
          assert isinstance(
              tuning.trials[0],
              rankweave.WeightedConvexTuningTrial,
          )
          PY
"""
_replace_once(
    ".github/workflows/ci.yml",
    CI_SMOKE_MARKER,
    CI_SMOKE_REPLACEMENT,
)
