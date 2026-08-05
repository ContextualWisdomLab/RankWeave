"""Apply reviewed RankWeave 0.17.0 metadata to PR 32."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()


def read(path_text: str) -> str:
    """Read one target repository file as UTF-8."""
    return (ROOT / path_text).read_text(encoding="utf-8")


def write(path_text: str, content: str) -> None:
    """Write one target repository file as UTF-8."""
    (ROOT / path_text).write_text(content, encoding="utf-8")


def replace_all(path_text: str, old: str, new: str) -> None:
    """Replace every matching release token when it is present."""
    content = read(path_text)
    if old in content:
        write(path_text, content.replace(old, new))


def insert_before(path_text: str, marker: str, addition: str) -> None:
    """Insert one idempotent documentation section before a unique marker."""
    content = read(path_text)
    if addition.strip() in content:
        return
    if content.count(marker) != 1:
        raise SystemExit(f"{path_text}: expected one marker {marker!r}")
    write(path_text, content.replace(marker, addition + marker, 1))


for path_text in (
    "uv.lock",
    "README.md",
    "docs/releasing.md",
    "tests/test_verify_artifacts_cli.py",
):
    replace_all(path_text, "0.16.0", "0.17.0")

CHANGELOG_ENTRY = """## [0.17.0] - 2026-08-05

### Added
- Public `WeightedConvexBacktestWindowDefinition`,
  `WeightedConvexBacktestWindow`, `WeightedConvexBacktestReport`, and
  `backtest_weighted_convex_fusion` APIs for availability-time-respecting
  historical assessment of fixed convex score-fusion policy selection.
- Exact per-window training and held-out membership, normalized UTC time bounds,
  full tuning evidence, selected fixed weights, held-out rankings and metrics,
  one original-order out-of-sample evaluation, and a separately labelled
  all-data final tuning recommendation.
- Dedicated temporal backtesting documentation, an accepted ADR, release
  packaging smoke, and APA 7th grounding in Tashman (2000), Bergmeir and
  Benítez (2012), and Cerqueira et al. (2020).

### Validation
- Scored results, judgments, and availability timestamps must contain exactly
  the same non-empty query set; availability timestamps must be timezone-aware.
- Caller-defined windows must be unique, ordered, non-overlapping, complete, and
  strictly forward in UTC. A future assessment query cannot appear in an
  earlier training set, and same-instant training and assessment are rejected.
- Selection is performed only on each window's declared training queries. The
  chosen fixed policy is applied unchanged to held-out queries.

### Compatibility
- Runtime remains standard-library-only, Python 3.10+, deterministic,
  store-agnostic, standalone-usable, and suitable for naruon or another MSA
  consumer. RankWeave does not infer timestamps, generate windows, access a
  database, or claim that all-data final tuning is out-of-sample evidence.

"""
insert_before(
    "CHANGELOG.md",
    "## [0.16.0] - 2026-08-05\n",
    CHANGELOG_ENTRY,
)

README_SECTION = """## Backtest convex policies by availability time

Use `backtest_weighted_convex_fusion` when a policy must be selected only from
information available before each historical assessment window. The caller
supplies timezone-aware availability timestamps and explicit ordered windows;
RankWeave rejects future-evidence leakage, overlapping held-out windows,
incomplete query accounting, and ambiguous same-instant boundaries.

Each window preserves the complete training tuning report, selected fixed
weights, held-out rankings, and held-out evaluation. The report also reconstructs
one original-order out-of-sample evaluation and keeps the all-data final policy
recommendation separate from prospective evidence.

See [Temporal convex-fusion backtesting](docs/temporal-convex-backtesting.md).

"""
insert_before(
    "README.md",
    "## Input and determinism guarantees\n",
    README_SECTION,
)

ARCHITECTURE_SECTION = """## Availability-time backtesting boundary

`temporal_backtesting.py` is deterministic experiment orchestration. It delegates
policy selection to `tune_weighted_convex_fusion`, list fusion to
`weighted_convex_fuse`, and effectiveness calculation to `evaluate_rankings`.
The caller owns availability provenance and explicit assessment windows.
RankWeave normalizes aware datetimes to UTC, enforces strictly forward training
and held-out evidence, preserves every window result, reconstructs one
out-of-sample evaluation, and labels all-data final tuning separately.

"""
insert_before(
    "ARCHITECTURE.md",
    "## Compatibility and release policy\n",
    ARCHITECTURE_SECTION,
)
replace_all(
    "ARCHITECTURE.md",
    "- `tuning.py` — validation-set convex-score and weighted-RRF policy selection.\n",
    "- `tuning.py` — validation-set convex-score and weighted-RRF policy selection.\n"
    "- `temporal_backtesting.py` — availability-time historical policy assessment.\n",
)

AGENTS_SECTION = """- **Availability time is the experiment clock.** Temporal backtests require
  caller-proven, timezone-aware availability timestamps. Training evidence must
  precede every held-out window strictly, future assessment queries may not enter
  earlier training sets, and all-data final tuning must remain distinct from
  out-of-sample performance.

"""
insert_before("AGENTS.md", "## Develop\n", AGENTS_SECTION)
replace_all(
    "AGENTS.md",
    "- `src/rankweave/tuning.py` — validation-set convex-score and weighted-RRF policy selection.\n",
    "- `src/rankweave/tuning.py` — validation-set convex-score and weighted-RRF policy selection.\n"
    "- `src/rankweave/temporal_backtesting.py` — availability-time backtesting and audit evidence.\n",
)

CLAUDE_SECTION = """## Temporal backtesting

Treat availability time as a required evidence boundary, not a convenience
sort key. Keep windows caller-owned, explicit, complete, strictly forward, and
free of future assessment queries in earlier training sets. Preserve full
window evidence and never describe all-data final tuning as held-out quality.

"""
insert_before("CLAUDE.md", "## Artifact verification\n", CLAUDE_SECTION)

RESEARCH_SECTION = """## Availability-time backtesting

`backtest_weighted_convex_fusion` evaluates an ordered sequence of explicit
historical assessment windows. It uses the earliest time at which each query's
complete scored results and judgments were available, rather than event or
creation time, and requires every training timestamp to precede the next
held-out window strictly. Each selected fixed policy is applied unchanged to its
held-out queries. The reconstructed aggregate is out-of-sample evidence for the
declared selection procedure; the separate all-data final tuning report is a
future recommendation, not held-out performance.

This contract follows rolling-origin and time-series performance-estimation
literature while remaining conservative about scope: RankWeave does not infer a
stochastic time-series model, establish causality, or validate the provenance of
a caller-supplied availability timestamp.

Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time
series predictor evaluation. *Information Sciences, 191*, 192–213.
https://doi.org/10.1016/j.ins.2011.12.028

Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series
forecasting models: An empirical study on performance estimation methods.
*Machine Learning, 109*(11), 1997–2028.
https://doi.org/10.1007/s10994-020-05910-7

Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis
and review. *International Journal of Forecasting, 16*(4), 437–450.
https://doi.org/10.1016/S0169-2070(00)00065-0

"""
insert_before(
    "docs/research/README.md",
    "## TREC interchange contract\n",
    RESEARCH_SECTION,
)
