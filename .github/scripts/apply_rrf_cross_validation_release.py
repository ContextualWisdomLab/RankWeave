"""Apply reviewed RankWeave 0.18.0 weighted-RRF release metadata."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path_text: str) -> str:
    """Read one repository file as UTF-8."""
    return (ROOT / path_text).read_text(encoding="utf-8")


def write(path_text: str, content: str) -> None:
    """Write one repository file as UTF-8."""
    (ROOT / path_text).write_text(content, encoding="utf-8")


def replace_all(path_text: str, old: str, new: str) -> None:
    """Replace all occurrences and fail when the expected token is absent."""
    content = read(path_text)
    if old not in content:
        raise SystemExit(f"{path_text}: replacement target {old!r} is absent")
    write(path_text, content.replace(old, new))


def insert_before(path_text: str, marker: str, addition: str) -> None:
    """Insert one idempotent section before a unique marker."""
    content = read(path_text)
    if addition.strip() in content:
        return
    if content.count(marker) != 1:
        raise SystemExit(f"{path_text}: expected one marker {marker!r}")
    write(path_text, content.replace(marker, addition + marker, 1))


for version_path in (
    "pyproject.toml",
    "src/rankweave/__init__.py",
    "tests/test_version.py",
    "tests/test_verification_schema.py",
    "tests/test_verify_artifacts_cli.py",
    "tests/test_temporal_release_contract.py",
    "uv.lock",
    "README.md",
    "docs/releasing.md",
    ".github/workflows/ci.yml",
):
    replace_all(version_path, "0.17.0", "0.18.0")

CHANGELOG_ENTRY = """## [0.18.0] - 2026-08-05

### Added
- Public `WeightedRRFCrossValidationFold`,
  `WeightedRRFCrossValidationReport`, and
  `cross_validate_weighted_reciprocal_rank_fusion` APIs for blocked-fold
  assessment of fixed weighted reciprocal-rank-fusion policy selection.
- Complete immutable training tuning and held-out evaluation evidence for every
  fold, one original-query-order out-of-fold evaluation, a fixed
  `rank_constant_eta`, and a separately labelled all-data final tuning
  recommendation.
- Dedicated rank-only cross-validation documentation, package-root exports,
  installed-wheel smoke, architecture and agent contracts, and APA 7th research
  grounding.

### Changed
- Convex and weighted-RRF cross-validation now share one fail-closed request
  validator for cutoff, objective, candidate family, query/judgment parity,
  exact fold assignment, fold identifier hashability, and minimum fold count.
- Existing convex cross-validation public behavior and record names remain
  unchanged.

### Validation
- Weighted-RRF folds require unique hashable item IDs, complete channel weights,
  convex weight domains, a positive integer eta, and at least two explicit
  caller-owned folds.
- The same eta and selected fixed weights are used for training tuning, held-out
  fusion, and final tuning. Cross-validation remains selection-procedure
  evidence; final effectiveness requires an independent test set.

### Compatibility
- Runtime remains standard-library-only, Python 3.10+, deterministic,
  store-agnostic, standalone-usable, and suitable for naruon or another MSA
  consumer. No database, network, provider, LLM, UI, scheduler, or credential
  dependency is introduced.

"""
insert_before(
    "CHANGELOG.md",
    "## [0.17.0] - 2026-08-05\n",
    CHANGELOG_ENTRY,
)

README_SECTION = """## Cross-validate fixed weighted-RRF policies

Rank-only retrieval systems can evaluate their complete fixed-weight selection
procedure with explicit blocked folds:

```python
from rankweave import cross_validate_weighted_reciprocal_rank_fusion

report = cross_validate_weighted_reciprocal_rank_fusion(
    channel_rankings_by_query,
    relevance_by_query,
    candidate_channel_weights,
    fold_id_by_query,
    cutoff=10,
    rank_constant_eta=60,
)
```

Every fold tunes weights only on complementary training queries, applies the
selected weights and one fixed eta unchanged to held-out rank lists, and retains
the complete tuning and evaluation reports. The aggregate out-of-fold result is
kept separate from all-data final tuning. The caller owns leakage-safe grouping
for translations, users, tenants, revisions, projects, events, and time blocks.

See [Weighted-RRF explicit-fold cross-validation](docs/rrf-cross-validation.md).

"""
insert_before(
    "README.md",
    "## Backtest convex policies by availability time\n",
    README_SECTION,
)

ARCHITECTURE_SECTION = """## Rank-only cross-validation boundary

`cross_validation.py` keeps convex and weighted-RRF public APIs explicit while
sharing request validation. The RRF path delegates selection to
`tune_weighted_reciprocal_rank_fusion`, fusion to
`weighted_reciprocal_rank_fuse`, and metrics to `evaluate_rankings`. One fixed
eta is carried through every fold and final tuning. Fold construction and
leakage control remain caller responsibilities.

"""
insert_before(
    "ARCHITECTURE.md",
    "## Availability-time backtesting boundary\n",
    ARCHITECTURE_SECTION,
)

AGENT_RULE = """- **RRF cross-validation preserves native semantics.** Rank-only fold
  assessment must delegate to `tune_weighted_reciprocal_rank_fusion`,
  `weighted_reciprocal_rank_fuse`, and `evaluate_rankings`; use one fixed eta,
  preserve explicit fold order, and keep final all-data tuning distinct from
  out-of-fold evidence.
"""
insert_before(
    "AGENTS.md",
    "- **Strict TREC boundaries.**",
    AGENT_RULE,
)
replace_all(
    "AGENTS.md",
    "- `src/rankweave/comparison.py` — exact and Monte Carlo paired randomization.\n",
    "- `src/rankweave/comparison.py` — exact and Monte Carlo paired randomization.\n"
    "- `src/rankweave/cross_validation.py` — blocked convex and weighted-RRF policy assessment.\n",
)

CLAUDE_SECTION = """## Weighted-RRF cross-validation

Keep rank-only fold assessment as deterministic composition of the native RRF
tuner, fusion primitive, and evaluation API. Preserve one fixed eta, caller fold
order, complete per-fold evidence, exact query-set parity, and the independent
final-test boundary. Do not introduce hidden folds, adaptive weights, or a
second rank-fusion implementation.

"""
insert_before("CLAUDE.md", "## Temporal backtesting\n", CLAUDE_SECTION)

RESEARCH_SECTION = """### Weighted-RRF blocked folds

`cross_validate_weighted_reciprocal_rank_fusion` extends the explicit-fold
selection boundary to rank-only channels. Every fold tunes fixed convex channel
weights through the native weighted-RRF tuner, applies those weights with one
unchanged eta to held-out queries, and preserves the full training and held-out
evidence. Cormack et al. (2009) ground RRF, Samuel et al. (2025) ground unequal
channel reliability, and Stone (1974), Cawley and Talbot (2010), and Roberts et
al. (2017) ground the separation of selection, assessment, and dependent-data
blocking.

The library does not generate folds or claim that a supplied grouping is
leakage-safe. The all-data winner remains a future recommendation rather than an
out-of-fold quality estimate.

"""
insert_before(
    "docs/research/README.md",
    "## Availability-time backtesting\n",
    RESEARCH_SECTION,
)

CI_SMOKE_MARKER = """          assert isinstance(
              backtest.windows[0],
              rankweave.WeightedConvexBacktestWindow,
          )
          PY
"""
CI_SMOKE_REPLACEMENT = """          assert isinstance(
              backtest.windows[0],
              rankweave.WeightedConvexBacktestWindow,
          )

          rrf_cross_validation = (
              rankweave.cross_validate_weighted_reciprocal_rank_fusion(
                  {
                      "q1": {
                          "lexical": ["a", "x"],
                          "dense": ["x", "a"],
                      },
                      "q2": {
                          "lexical": ["y", "b"],
                          "dense": ["b", "y"],
                      },
                      "q3": {
                          "lexical": ["c", "z"],
                          "dense": ["z", "c"],
                      },
                      "q4": {
                          "lexical": ["w", "d"],
                          "dense": ["d", "w"],
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
                  rank_constant_eta=17,
              )
          )
          assert len(rrf_cross_validation.folds) == 2
          assert rrf_cross_validation.rank_constant_eta == 17
          assert (
              rrf_cross_validation.out_of_fold_evaluation.aggregate.query_count
              == 4
          )
          assert isinstance(
              rrf_cross_validation,
              rankweave.WeightedRRFCrossValidationReport,
          )
          assert isinstance(
              rrf_cross_validation.folds[0],
              rankweave.WeightedRRFCrossValidationFold,
          )
          PY
"""
if CI_SMOKE_MARKER not in read(".github/workflows/ci.yml"):
    raise SystemExit("ci.yml: installed temporal smoke marker is absent")
write(
    ".github/workflows/ci.yml",
    read(".github/workflows/ci.yml").replace(
        CI_SMOKE_MARKER,
        CI_SMOKE_REPLACEMENT,
        1,
    ),
)
write(".github/generated-ci.yml", read(".github/workflows/ci.yml"))
