# CLAUDE.md — RankWeave

All automated contributors must follow [`AGENTS.md`](AGENTS.md) and the
architectural boundaries in [`ARCHITECTURE.md`](ARCHITECTURE.md).

RankWeave is a standard-library-only runtime. Keep statistical arithmetic in
the pure Python core, keep CLI behavior as a transport adapter, preserve
standalone and naruon/MSA use, write tests before behavior changes, and maintain
100% production statement and branch coverage plus complete public docstrings.

Report JSON Schemas are public compatibility resources. Any transport change
requires synchronized schema, tests, installed-wheel smoke, documentation, and
release metadata. Do not use `COPILOT_GITHUB_TOKEN`; the governed product loop
uses the existing `NVIDIA_NIM_API_KEY` OpenCode path without altering review
agent credentials.

## Convex score-fusion tuning

Keep scored-policy selection as deterministic composition of
`weighted_convex_fuse` and `evaluate_rankings`. Preserve every trial, caller
weight order, exact first-policy ties, query-set parity, and the independent
held-out-test boundary. Do not add a runtime optimizer or numerical dependency.

## Explicit-fold cross-validation

Keep folds caller-owned and immutable. Tune each policy only on the complementary
queries, apply it unchanged to held-out queries, reconstruct out-of-fold metrics
in original query order, and keep the all-data deployment recommendation
separate from held-out evidence. Do not add random splitting, hidden grouping,
or duplicate fusion and evaluation arithmetic.

## Weighted-RRF cross-validation

Keep rank-only fold assessment as deterministic composition of the native RRF
tuner, fusion primitive, and evaluation API. Preserve one fixed eta, caller fold
order, complete per-fold evidence, exact query-set parity, and the independent
final-test boundary. Do not introduce hidden folds, adaptive weights, or a
second rank-fusion implementation.

## Temporal backtesting

Treat availability time as a required evidence boundary, not a convenience
sort key. Keep windows caller-owned, explicit, complete, strictly forward, and
free of future assessment queries in earlier training sets. Preserve full
window evidence and never describe all-data final tuning as held-out quality.

## Artifact verification

Keep the verification core standard-library-only and transport-neutral. Filesystem and JSON concerns belong in the CLI adapter. A mismatch is a normal machine-readable exit-1 result; malformed evidence remains stderr-only exit 2. Every new output field requires schema, docs, wheel-smoke, and coverage updates.

## Release workflow

`.github/workflows/publish.yml` is a security-sensitive distribution boundary. Keep build, provenance, and publication in separate least-privilege jobs. Publication is release-only, environment-gated, tokenless, and fail-closed. Version-bearing files, CHANGELOG, archive contents, action SHAs, and attestation documentation must change together. A provenance attestation is not a claim of package correctness or scientific validity.

## Package CI action runtime

Repository-owned package-CI JavaScript actions must use reviewed Node.js 24-compatible releases pinned to full commit SHAs. Moving action tags and runner compatibility-warning fallbacks are not accepted trust inputs. Changes to the privileged hourly commercialization workflow remain a separate control-plane review scope.
