# RankWeave Architecture

## Purpose

RankWeave is a Python library and command-line component backed by one Rust
calculation core and no third-party Python runtime dependency. It provides
retrieval-score fusion, ranking evaluation, paired and candidate-family
comparison, policy tuning, strict TREC interchange, and auditable report
transport. It operates as a standalone package and as a bounded module inside
naruon or another service-oriented system.

## Architectural boundaries

1. **Pure calculation core** — fusion, evaluation, randomization, Holm
   correction, tuning, and exact semantic indexing accept in-memory values and
   perform no network, database, provider, or filesystem access. Immutable
   semantic snapshots precompute digest-bound scale and norm metadata, then
   atomically replace only after complete validation (ADR 0008).
2. **Interchange adapters** — TREC parsers and formatters convert strict text
   artifacts to immutable domain records.
3. **Transport adapters** — the CLI performs bounded local reads and delegates
   all statistical work to the public Python APIs.
4. **Contract resources** — packaged JSON Schema Draft 2020-12 documents publish
   the exact pairwise and candidate-family v1/v2 JSON structures without adding
   a runtime validator dependency.
5. **Governed delivery** — repository workflows call immutable central `.github`
   review and merge workflows. The hourly product loop uses a hash-pinned
   OpenCode executable and `NVIDIA_NIM_API_KEY`; it does not use
   `COPILOT_GITHUB_TOKEN`.

## Data flow

```text
local run and qrels artifacts
  -> bounded strict-UTF-8 adapter
  -> immutable TREC records
  -> evaluation and statistical comparison core
  -> versioned JSON projection
  -> optional exact-byte SHA-256 evidence
  -> packaged machine-readable schema validation by the consumer
```

The default v1 transports remain stable. Opt-in v2 transports add path-free
artifact digests. Machine-readable schema resources describe both versions but
do not authenticate producers, verify external artifact bytes, or establish
scientific validity.

## Module map

- `score_fusion.py` — scalar fusion primitives.
- `semantic_vector_ranking.py` — typed adapter to Rust-owned semantic-unit
  cosine ranking; authorization and embedding generation remain upstream.
- `semantic_index.py` — typed adapter to immutable exact Rust index snapshots;
  the caller owns persistence, model selection, and authorized candidate IDs.
- `ranked_list_fusion.py` — complete-list fusion and contribution evidence.
- `evaluation.py` — precision, recall, reciprocal rank, and graded nDCG.
- `comparison.py` — exact and deterministic Monte Carlo paired randomization.
- `cross_validation.py` — caller-owned blocked folds, fold-local policy selection, and out-of-fold evaluation.
- `tuning.py` — validation-set convex-score and weighted-RRF policy selection.
- `temporal_backtesting.py` — availability-time historical policy assessment.
- `trec.py` — strict TREC parsing, formatting, and evaluation.
- `trec_comparison.py` — direct pairwise TREC comparison orchestration.
- `trec_family_comparison.py` — ordered family comparison and Holm correction.
- `cli.py` — bounded local-file and UTF-8 JSON transport adapter.
- `report_schemas.py` — stable schema discovery and package-resource loading.
- `schemas/` — Draft 2020-12 report contracts shipped in the wheel.

## Offline policy-selection boundary

`tuning.py` defines deterministic experiment orchestration, not a second fusion
or metric engine. Convex score policies delegate to `weighted_convex_fuse`;
weighted-RRF policies delegate to `weighted_reciprocal_rank_fuse`; both delegate
all effectiveness calculation to `evaluate_rankings`. Candidate insertion order
is preserved as the exact tie breaker, and every trial retains its complete
immutable evaluation. Grid generation, score normalization, validation splits,
cross-validation, and final held-out inference remain caller responsibilities.

## Explicit-fold assessment boundary

`cross_validation.py` evaluates the policy-selection procedure rather than
relabeling full-data tuning as test performance. Each fold delegates selection
to `tune_weighted_convex_fusion`, held-out fusion to `weighted_convex_fuse`, and
all metrics to `evaluate_rankings`. Fold order follows first query appearance;
training, held-out, and reconstructed out-of-fold query order remain explicit.
The caller owns fold grouping because only the consumer knows which translations,
revisions, users, tenants, events, projects, or time windows must not cross the
training boundary. Random fold generation and rolling-origin forecasting are
outside this module.

## Rank-only cross-validation boundary

`cross_validation.py` keeps convex and weighted-RRF public APIs explicit while
sharing request validation. The RRF path delegates selection to
`tune_weighted_reciprocal_rank_fusion`, fusion to
`weighted_reciprocal_rank_fuse`, and metrics to `evaluate_rankings`. One fixed
eta is carried through every fold and final tuning. Fold construction and
leakage control remain caller responsibilities.

## Availability-time backtesting boundary

`temporal_backtesting.py` is deterministic experiment orchestration. It delegates
policy selection to `tune_weighted_convex_fusion`, list fusion to
`weighted_convex_fuse`, and effectiveness calculation to `evaluate_rankings`.
The caller owns availability provenance and explicit assessment windows.
RankWeave normalizes aware datetimes to UTC, enforces strictly forward training
and held-out evidence, preserves every window result, reconstructs one
out-of-sample evaluation, and labels all-data final tuning separately.

## Compatibility and release policy

Public behavior changes are additive unless a new transport schema identifier is
introduced. A release synchronizes package metadata, public version, version
tests, installed-wheel assertions, documentation, and `CHANGELOG.md`. Every
production statement and branch, plus every public module, class, function, and
method docstring, remains covered by the repository quality gates.

## Exact artifact-verification boundary

`artifact_verification.py` is a pure bytes-and-mappings core with no filesystem, JSON, provider, network, or database access. `cli.py` is the bounded filesystem and strict RFC 8259 boundary. The output transport is path-free and independently reusable by naruon or another MSA consumer. SHA-256 equality is deliberately separated from authentication and provenance policy.

## Governed release boundary

Release authorization and package publication are different trust domains.
`create-release.yml` first verifies the exact default-branch commit, synchronized
0.18.0 identity, missing public PyPI version, missing tag and release, full tests,
100% statement/branch coverage, distribution names, and deterministic CHANGELOG
notes with `contents: read` only.

The protected `pypi` environment release job receives only `contents: write` and
creates a stable GitHub Release targeted at that verified SHA. Because GitHub
suppresses ordinary workflow events generated with the repository
`GITHUB_TOKEN`, a distinct job with only `actions: write` starts the explicit
`workflow_dispatch` interface of `publish.yml`. This avoids a personal access
token or GitHub App private key while keeping release and dispatch authority
separate.

`publish.yml` independently accepts an external stable release event or the
explicit tag/SHA dispatch. Its read-only build job verifies the existing GitHub
Release, tag-to-commit identity, default-branch reachability, package version,
complete quality gate, and platform-wheel/source contents. It records a SHA-256
manifest and uploads the Linux, macOS, and Windows wheels, source distribution,
and that manifest as one immutable Actions artifact.

Separate provenance and publication jobs verify the handoff before use. The
provenance job creates GitHub build-provenance attestations. The protected
`pypi` job exchanges GitHub OIDC for a short-lived PyPI Trusted Publishing
credential. No long-lived registry credential, force-moving tag,
`skip-existing`, or alternate registry exists. GitHub and PyPI attestations bind
statements to artifact digests; they do not establish statistical validity,
vulnerability absence, or downstream policy compliance.
