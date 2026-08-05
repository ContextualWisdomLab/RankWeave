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
- `tuning.py` — validation-set weighted-RRF policy selection.
- `trec.py` — strict TREC parsing, formatting, and evaluation.
- `trec_comparison.py` — direct pairwise TREC comparison orchestration.
- `trec_family_comparison.py` — ordered family comparison and Holm correction.
- `cli.py` — bounded local-file and UTF-8 JSON transport adapter.
- `report_schemas.py` — stable schema discovery and package-resource loading.
- `schemas/` — Draft 2020-12 report contracts shipped in the wheel.

## Compatibility and release policy

Public behavior changes are additive unless a new transport schema identifier is
introduced. A release synchronizes package metadata, public version, version
tests, installed-wheel assertions, documentation, and `CHANGELOG.md`. Every
production statement and branch, plus every public module, class, function, and
method docstring, remains covered by the repository quality gates.

## Exact artifact-verification boundary

`artifact_verification.py` is a pure bytes-and-mappings core with no filesystem, JSON, provider, network, or database access. `cli.py` is the bounded filesystem and strict RFC 8259 boundary. The output transport is path-free and independently reusable by naruon or another MSA consumer. SHA-256 equality is deliberately separated from authentication and provenance policy.

## Governed release boundary

A published GitHub Release is the only publication trigger. A read-only exact-tag build job verifies tag and package version identity, runs the complete quality gate, builds one wheel and one source distribution, and uploads one immutable Actions artifact. Separate jobs download that artifact with digest mismatch configured to fail: the provenance job creates GitHub build-provenance attestations, and the protected `pypi` environment job exchanges GitHub OIDC for a short-lived PyPI publishing credential.

The repository stores no package-registry credential and provides no token fallback. GitHub and PyPI attestations bind signed statements to exact artifact digests; they do not establish statistical validity, vulnerability absence, or downstream policy compliance.
