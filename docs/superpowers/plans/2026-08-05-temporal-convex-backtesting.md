# Temporal convex-fusion backtesting implementation plan

> Execute test-first and preserve the standard-library-only runtime.

## Goal

Add auditable time-respecting backtesting for fixed convex scored-channel policy selection, release it as RankWeave 0.17.0, and preserve standalone plus naruon/MSA use.

## Task 1 — Define failing behavior contracts

Create `tests/test_temporal_backtesting.py` covering:

- two ordered assessment windows with expanding training evidence;
- exact held-out rankings and original-order out-of-sample reconstruction;
- separate all-data final tuning;
- all supported tuning objectives;
- immutable public records;
- timezone normalization to UTC;
- non-datetime and naive timestamps;
- timestamp-query mismatch;
- duplicate or unhashable window IDs;
- duplicate training and held-out query IDs;
- empty training or held-out windows;
- unknown query IDs and within-window overlap;
- future or same-time training evidence;
- repeated held-out queries;
- non-monotone held-out time ranges;
- missing query accounting and warm-up queries later held out;
- invalid cutoff, objective, policies, scores, and duplicate items.

Run the focused tests and confirm they fail because the module does not exist.

## Task 2 — Implement the pure orchestration core

Create `src/rankweave/temporal_backtesting.py`.

- Define frozen window-definition, window-result, and report dataclasses.
- Validate and normalize timezone-aware datetimes to UTC.
- Snapshot explicit window sequences and query ID sequences to tuples.
- Validate complete query accounting and strict temporal order.
- Delegate training selection to `tune_weighted_convex_fusion`.
- Delegate held-out fusion to `weighted_convex_fuse`.
- Delegate all metric calculation to `evaluate_rankings`.
- Preserve exact held-out and aggregate out-of-sample rankings.
- Compute a separate all-data final tuning report.
- Add complete public docstrings.

Run focused tests until green and confirm module line and branch coverage is 100%.

## Task 3 — Publish the API and release metadata

- Export the new records and function from `rankweave.__init__`.
- Synchronize `pyproject.toml`, `rankweave.__version__`, `uv.lock`, version tests, README, release guidance, and CHANGELOG at 0.17.0.
- Add `docs/temporal-convex-backtesting.md`.
- Update `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/research/README.md`.
- Add an accepted ADR for availability-time and rolling-origin boundaries.
- Keep the three references in APA 7th format.

## Task 4 — Strengthen package and release gates

- Require `rankweave/temporal_backtesting.py` in wheel checks and trusted release archive checks.
- Execute a real installed-wheel two-window backtest outside the source tree.
- Keep every external Action pinned to a full commit SHA.

## Task 5 — Exact-head verification and merge

Run:

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

Then require Python 3.10–3.13 CI, package smoke, Security Scan, SAST, current-head review, and zero unresolved threads. Remove all temporary updater files before marking the PR ready. Merge only the exact verified head.
