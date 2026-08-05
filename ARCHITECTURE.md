# RankWeave Architecture

## Purpose

RankWeave is a dependency-free Python library and command-line component for
retrieval-score fusion, ranking evaluation, paired and candidate-family
comparison, policy tuning, strict TREC interchange, and auditable report
transport. It operates as a standalone package and as a bounded module inside
naruon or another service-oriented system.

## Architectural boundaries

1. **Pure calculation core** — fusion, evaluation, randomization, Holm
   correction, and tuning accept in-memory values and perform no network,
   database, provider, or filesystem access.
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

A published stable GitHub Release is the only publication trigger. A read-only exact-tag build job verifies release-event commit identity, default-branch reachability, tag and package version identity, the complete quality gate, and both wheel and source-distribution contents. It records a SHA-256 manifest for the two distributions and uploads the files plus that manifest as one immutable Actions artifact.

Separate provenance and publication jobs download the immutable artifact, verify the manifest itself against a build-job output, verify both distribution hashes, and only then use the files. The provenance job creates GitHub build-provenance attestations for the wheel and source distribution. The protected `pypi` environment job exchanges GitHub OIDC for a short-lived PyPI publishing credential.

The official download action's built-in artifact digest validation is useful but reports a mismatch as a warning rather than a failing input contract. RankWeave therefore performs its own checksum-manifest verification and never passes an unsupported `digest-mismatch` input. The repository stores no package-registry credential and provides no token fallback. GitHub and PyPI attestations bind signed statements to exact artifact digests; they do not establish statistical validity, vulnerability absence, or downstream policy compliance.
