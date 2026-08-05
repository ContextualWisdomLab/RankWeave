"""Apply the reviewed RankWeave 0.16.0 cross-validation release edits."""

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
    _replace_all(version_path, "0.15.0", "0.16.0")

README_SECTION = """## Cross-validate convex score-fusion selection

```python
from rankweave import cross_validate_weighted_convex_fusion

report = cross_validate_weighted_convex_fusion(
    scored_results_by_query,
    relevance_by_query,
    {
        "dense-heavy": {"lexical": 0.1, "dense": 0.9},
        "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
    },
    {
        "query-a1": "source-family-a",
        "query-a2": "source-family-a",
        "query-b1": "source-family-b",
        "query-b2": "source-family-b",
    },
    cutoff=10,
)

print(report.out_of_fold_evaluation.aggregate.mean_ndcg_at_k)
print(report.final_tuning.best_policy_id)
```

Every held-out fold is evaluated with a policy selected only from the remaining
queries. Fold IDs are caller-owned so translations, paraphrases, revisions,
tenants, projects, events, or time blocks can remain together when the
experimental boundary requires it. The out-of-fold evaluation estimates the
selection procedure under that exact fold design; the separate full-data tuning
report recommends one future policy and is not held-out evidence.

See [Explicit-fold convex fusion cross-validation](docs/convex-fusion-cross-validation.md).

"""
_insert_before(
    "README.md",
    "## Tune a fixed convex score-fusion policy\n",
    README_SECTION,
)

_replace_once(
    "ARCHITECTURE.md",
    "- `comparison.py` — exact and deterministic Monte Carlo paired randomization.\n",
    "- `comparison.py` — exact and deterministic Monte Carlo paired randomization.\n"
    "- `cross_validation.py` — caller-owned blocked folds, fold-local policy "
    "selection, and out-of-fold evaluation.\n",
)
_insert_before(
    "ARCHITECTURE.md",
    "## Compatibility and release policy\n",
    """## Explicit-fold assessment boundary

`cross_validation.py` evaluates the policy-selection procedure rather than
relabeling full-data tuning as test performance. Each fold delegates selection
to `tune_weighted_convex_fusion`, held-out fusion to `weighted_convex_fuse`, and
all metrics to `evaluate_rankings`. Fold order follows first query appearance;
training, held-out, and reconstructed out-of-fold query order remain explicit.
The caller owns fold grouping because only the consumer knows which translations,
revisions, users, tenants, events, projects, or time windows must not cross the
training boundary. Random fold generation and rolling-origin forecasting are
outside this module.

""",
)

AGENT_MARKER = """- **Convex tuning delegates rather than duplicates.** Scored-policy selection
  must call `weighted_convex_fuse` and `evaluate_rankings`, retain every full
  immutable evaluation, and treat the supplied policy order as audit evidence.
  Do not normalize provider scores, generate a hidden search space, or present
  validation selection as held-out effectiveness.
"""
AGENT_REPLACEMENT = AGENT_MARKER + """- **Cross-validation folds are caller-owned.** Explicit-fold assessment must
  tune only on the complementary queries, apply the selected fixed policy
  unchanged to held-out queries, restore original query order for out-of-fold
  evidence, and keep full-data final tuning separate. Never generate hidden
  random folds or imply that an arbitrary grouping is leakage-safe.
"""
_replace_once("AGENTS.md", AGENT_MARKER, AGENT_REPLACEMENT)
_replace_once(
    "AGENTS.md",
    "- `src/rankweave/comparison.py` — exact and Monte Carlo paired randomization.\n",
    "- `src/rankweave/comparison.py` — exact and Monte Carlo paired randomization.\n"
    "- `src/rankweave/cross_validation.py` — explicit blocked folds, "
    "fold-local selection, and out-of-fold evidence.\n",
)
_replace_once(
    "AGENTS.md",
    "- `src/rankweave/tuning.py` — validation-set weighted-RRF policy selection.\n",
    "- `src/rankweave/tuning.py` — validation-set convex-score and "
    "weighted-RRF policy selection.\n",
)

_insert_before(
    "CLAUDE.md",
    "## Artifact verification\n",
    """## Explicit-fold cross-validation

Keep folds caller-owned and immutable. Tune each policy only on the complementary
queries, apply it unchanged to held-out queries, reconstruct out-of-fold metrics
in original query order, and keep the all-data deployment recommendation
separate from held-out evidence. Do not add random splitting, hidden grouping,
or duplicate fusion and evaluation arithmetic.

""",
)

TUNING_RESEARCH_MARKER = """The selected validation policy is not an unbiased final effectiveness estimate.
Consumers must freeze the chosen weights and evaluate them once on an
independent held-out test set before making a production-quality claim.

"""
TUNING_RESEARCH_REPLACEMENT = TUNING_RESEARCH_MARKER + """## Explicit-fold cross-validation protocol

`cross_validate_weighted_convex_fusion` executes caller-defined blocked folds.
Each fold selects a fixed policy on the complementary queries and evaluates that
policy unchanged on held-out queries. It then reconstructs one out-of-fold
ranking map in original query order and separately tunes all judged queries to
recommend a future deployment policy.

Stone (1974) distinguishes cross-validatory choice from assessment. Cawley and
Talbot (2010) show that optimizing a noisy selection criterion can itself
overfit, producing selection bias when model choice and performance assessment
collapse. Roberts et al. (2017) show that random folds can underestimate error
under temporal, spatial, hierarchical, and related dependence and recommend
blocks aligned with the data structure. RankWeave therefore records explicit
caller-owned fold IDs rather than inventing a random split. Barata (2026,
preprint) provides a retrieval-specific example of training-fold weight
selection and held-out fold assessment.

The library cannot prove that a supplied grouping is leakage-safe. Consumers
must keep dependent translations, paraphrases, revisions, synthetic variants,
users, tenants, events, projects, or time windows together when the deployment
question requires it. Symmetric blocked folds are not automatically
rolling-origin forecasting evidence.

"""
_replace_once(
    "docs/research/README.md",
    TUNING_RESEARCH_MARKER,
    TUNING_RESEARCH_REPLACEMENT,
)
_insert_before(
    "docs/research/README.md",
    "Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion",
    """Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model
selection and subsequent selection bias in performance evaluation. *Journal of
Machine Learning Research, 11*, 2079–2107.
https://www.jmlr.org/papers/v11/cawley10a.html

""",
)
_insert_before(
    "docs/research/README.md",
    "Samuel, S., DeGenaro, D., Guallar-Blasco, J., Sanders, K., Eisape, O.,",
    """Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J.,
Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B.,
Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F.
(2017). Cross-validation strategies for data with temporal, spatial,
hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929.
https://doi.org/10.1111/ecog.02881

""",
)
_insert_before(
    "docs/research/README.md",
    "Smucker, M. D., Allan, J., & Carterette, B. (2007). A comparison of statistical",
    """Stone, M. (1974). Cross-validatory choice and assessment of statistical
predictions. *Journal of the Royal Statistical Society: Series B
(Methodological), 36*(2), 111–133.
https://doi.org/10.1111/j.2517-6161.1974.tb00994.x

""",
)

CHANGELOG_ENTRY = """## [0.16.0] - 2026-08-05

### Added
- Public `WeightedConvexCrossValidationFold`,
  `WeightedConvexCrossValidationReport`, and
  `cross_validate_weighted_convex_fusion` APIs for caller-owned blocked fold
  assessment of convex scored-channel policy selection.
- Fold-local training reports, immutable training and held-out query memberships,
  complete held-out evaluations, one original-order out-of-fold evaluation, and
  a separate full-data final policy recommendation.
- Dedicated leakage-boundary documentation and APA 7th grounding in Stone
  (1974), Cawley and Talbot (2010), Roberts et al. (2017), and a clearly
  identified 2026 retrieval preprint.

### Validation
- Scored results, judgments, and fold assignments must contain exactly the same
  non-empty query set; at least two distinct hashable fold identifiers are
  required.
- Every fold selects only on complementary queries and applies the selected
  weights unchanged to its held-out queries. Invalid scores, weights, duplicate
  items, undeclared channels, objectives, and cutoffs remain fail-closed through
  established public contracts.
- Explicit fold IDs make grouping auditable but do not prove a split is
  leakage-safe. Consumers remain responsible for keeping dependent query
  families and temporal blocks together when required.

### Compatibility
- Runtime remains standard-library-only, Python 3.10+, deterministic,
  store-agnostic, standalone-usable, and suitable for naruon or another MSA
  consumer. No random splitter, database, network, or numerical dependency is
  introduced.

"""
_insert_before(
    "CHANGELOG.md",
    "## [0.15.0] - 2026-08-05\n",
    CHANGELOG_ENTRY,
)

_replace_once(
    ".github/workflows/ci.yml",
    '              "rankweave/comparison.py",\n',
    '              "rankweave/comparison.py",\n'
    '              "rankweave/cross_validation.py",\n',
)

CI_SMOKE_MARKER = """          assert isinstance(
              tuning.trials[0],
              rankweave.WeightedConvexTuningTrial,
          )
          PY
"""
CI_SMOKE_REPLACEMENT = """          assert isinstance(
              tuning.trials[0],
              rankweave.WeightedConvexTuningTrial,
          )

          cross_validation = rankweave.cross_validate_weighted_convex_fusion(
              {
                  "q1": {
                      "lexical": [("a", 1.0), ("x", 0.0)],
                      "dense": [("x", 1.0), ("a", 0.0)],
                  },
                  "q2": {
                      "lexical": [("y", 1.0), ("b", 0.0)],
                      "dense": [("b", 1.0), ("y", 0.0)],
                  },
                  "q3": {
                      "lexical": [("c", 0.9), ("z", 0.1)],
                      "dense": [("z", 0.9), ("c", 0.1)],
                  },
                  "q4": {
                      "lexical": [("w", 0.9), ("d", 0.1)],
                      "dense": [("d", 0.9), ("w", 0.1)],
                  },
              },
              {
                  "q1": {"a": 1},
                  "q2": {"b": 1},
                  "q3": {"c": 1},
                  "q4": {"d": 1},
              },
              {
                  "dense-heavy": {"lexical": 0.1, "dense": 0.9},
                  "lexical-heavy": {"lexical": 0.9, "dense": 0.1},
              },
              {"q1": "a", "q2": "b", "q3": "a", "q4": "b"},
              cutoff=1,
          )
          assert len(cross_validation.folds) == 2
          assert cross_validation.out_of_fold_evaluation.aggregate.query_count == 4
          assert cross_validation.final_tuning.best_policy_id == "dense-heavy"
          assert isinstance(
              cross_validation,
              rankweave.WeightedConvexCrossValidationReport,
          )
          assert isinstance(
              cross_validation.folds[0],
              rankweave.WeightedConvexCrossValidationFold,
          )
          PY
"""
_replace_once(
    ".github/workflows/ci.yml",
    CI_SMOKE_MARKER,
    CI_SMOKE_REPLACEMENT,
)
