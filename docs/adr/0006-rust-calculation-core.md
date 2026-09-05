# ADR 0006: One Rust calculation core behind the public Python contract

- **Status: Proposed** — pending protected integration of PR #41.
- **Date:** 2026-08-26
- **Scope:** RankWeave fusion, evaluation, comparison, and policy-assessment arithmetic

## Context

RankWeave is the ecosystem owner for retrieval fusion and ranking evidence.
LineageWeave ADR 0225 forbids a second consumer-side arithmetic engine, while
RankWeave currently implements the production calculations in Python. Issue
#45 requires one Rust implementation without changing the research-grounded
public semantics or moving source access, authorization, retrieval, or provider
work into this package.

Parallel floating-point reduction cannot be introduced casually. Rayon states
that the reduction order of floating-point `sum` is unspecified, and NVIDIA
documents that parallel evaluation order and fused multiply-add can change a
floating-point result. An unspecified reduction order would break RankWeave's
deterministic result and tie contracts.

PyO3 supports native Python extension modules and Python's stable ABI. Maturin
supports mixed Python/Rust projects, allowing the established Python API and
type surface to remain the public adapter while wheel artifacts contain the
sole calculation implementation.

## Decision

RankWeave will use one Cargo workspace with two responsibility boundaries:

1. `rankweave-core` is a Python-independent Rust library containing validation,
   fusion, evaluation, comparison, and policy-assessment arithmetic.
2. `_rankweave_core` is a thin PyO3 extension. Existing Python modules validate
   transport types, translate stable public records, and call Rust; they do not
   retain a second calculation path.
3. Maturin builds the existing mixed Python package. The first Rust release
   targets the repository's minimum supported CPython stable ABI and retains
   the existing `rankweave` import and console entrypoints.

The engine accepts ordered caller evidence and an explicit policy envelope.
The envelope binds algorithm revision, policy revision, estimator identity,
estimator artifact digest, ordered active channels, and all numerical policy
values. A missing, mismatched, non-finite, or unproven policy fails closed.
RankWeave never estimates or renormalizes a policy inside a fusion request.

Candidate-level absence and channel-level unavailability remain distinct:

- when an explicitly active channel did not return one candidate, the existing
  documented theoretical-minimum contribution and missing-channel evidence are
  preserved;
- when the channel itself is unavailable, the caller must supply a separately
  estimated policy for the remaining exact channel set. RankWeave rejects an
  active-channel mismatch and never converts channel unavailability into a
  candidate-level zero.

The output envelope contains ordered results, per-channel score/rank/weight and
contribution evidence, missing-candidate markers, algorithm revision, policy
revision, estimator provenance, input digest, backend identity, and explicit
limitations. It contains no database identifier beyond opaque caller-owned
item/channel/query identifiers.

## CPU and GPU execution

The CPU backend uses Rust `f64`. Rayon may schedule independent candidates,
queries, or randomization draws, but it must not reduce the floating-point
terms of one score or metric in an unspecified order. Each scalar reduction
follows the documented caller order with the same operation sequence as the
reference vector; deterministic sorting applies the public tie contract after
parallel work completes.

The optional GPU backend is an explicit caller choice, never an automatically
selected size threshold. It uses CUDA double precision, fixed input order per
scalar result, no fast-math mode, and no contraction that changes the public
operation sequence. The backend is available only after the complete packaged
conformance vectors produce bit-identical finite output, ordering, contribution
evidence, validation errors, and digests against the CPU backend on that build.
If conformance fails or a compatible device is absent, a GPU request returns
backend-unavailable; it never falls back silently or substitutes a tolerance.

Benchmarks record exact source revision, backend revision, hardware, driver,
compiler flags, thread/device configuration, workload digest, distribution,
and result-conformance digest. RankWeave publishes no CPU/GPU throughput or
capacity claim without that artifact.

## Migration and compatibility

Migration is vertical by public operation, not a permanent dual engine:

1. freeze current public vectors, errors, ordered evidence, and artifact
   schemas as cross-language conformance fixtures;
2. implement and expose one operation in Rust;
3. switch its Python function to the extension and delete the corresponding
   Python arithmetic in the same change;
4. prove Python API, CPU, and optional GPU conformance plus complete Rust and
   Python coverage before moving the next operation; and
5. release immutable wheels before any consumer upgrades or deletes its own
   compatibility seam.

No environment flag may restore deleted Python arithmetic. An unsupported
platform receives an explicit installation or backend-unavailable failure;
source fallback is not a second production engine.

## Security and operability properties

### Proposed paired-p95 owner extension (2026-09-05)

The same calculation boundary applies to the gateway's missing paired-p95
comparison. `compare_paired_p95` accepts paired finite observations, an explicit
complete partition into resampling units, and a persisted draw plan. Rust owns
whole-unit expansion, inverse-empirical-CDF quantiles, candidate-minus-baseline
differences, percentile-replay endpoints and the ordered request digest.
Python transports typed values and projects the immutable report only.

```text
paired observations + complete units + explicit draws + row bound
  -> validate identities, partition, draw shape and expanded row counts
  -> same drawn units -> baseline p95 and candidate p95 -> subtract
  -> ordered replicate evidence + percentile endpoints + request digest
```

This avoids a second consumer engine and makes the draw plan auditable, at the
cost of retaining the plan and validating its inferential suitability outside
the replay operation. No RNG, inferred independence, cluster weighting or
automatic admission decision is added. In particular, the interval is not a
claim of calibrated coverage, and the original mixed-size units define an
observation-weighted distribution. Incomplete/multiple-membership or temporal
designs cannot be reinterpreted as supported disjoint units. The rationale,
alternatives, research and remaining release/calibration work are recorded in
[the paired-p95 contract](../paired-p95-comparison.md). This extension and ADR
remain Proposed until protected integration; no consumer pin is changed.

### Existing release properties

- Rust core inputs are bounded before allocation and reject duplicate,
  non-finite, and domain-invalid state.
- Python releases contain no provider, database, identity, or network client.
- Cargo, Python, and build-tool versions are immutable in lockfiles and CI.
- Wheels, SBOMs, attestations, schemas, type markers, and source revisions stay
  bound to the same release.
- Panic does not cross the extension boundary; public failures retain stable,
  documented Python exception classes.

## Consequences

- RankWeave no longer remains a pure-Python implementation, but the Python
  public surface and store-agnostic product boundary remain intact.
- Wheel coverage expands by operating system, architecture, and supported
  Python ABI; source-only installation requires the pinned Rust toolchain.
- Deterministic scalar arithmetic constrains where parallel reduction is legal.
- GPU acceleration remains optional and explicit because portability and exact
  evidence are more important than an inferred dispatch policy.
- LineageWeave can delete local fusion arithmetic only after a released
  RankWeave artifact and consumer-pin upgrade prove the full envelope.

## Rejected alternatives

- **Keep Python as the production arithmetic engine:** leaves the owning
  repository inconsistent with the ecosystem calculation boundary.
- **Retain Python as a runtime fallback:** creates the duplicate engine this
  decision removes and permits platform-dependent semantics.
- **Move fusion into TEPP or fast-mlsirm:** those products own measurement and
  estimation; they may produce policy provenance but do not own retrieval
  fusion.
- **Use Rayon floating-point `sum`:** its reduction order is unspecified.
- **Choose CPU or GPU from an item-count rule:** introduces an ungrounded
  heuristic and makes backend identity workload-dependent.
- **Accept an arbitrary CPU/GPU tolerance:** weakens exact contribution and tie
  evidence. A nonconforming GPU backend is unavailable instead.

## References — APA 7th edition

IEEE Computer Society. (2019). *IEEE standard for floating-point arithmetic*
(IEEE Std 754-2019). IEEE. https://doi.org/10.1109/IEEESTD.2019.8766229

NVIDIA Corporation. (2026). *CUDA C++ best practices guide* (Version 13.3).
https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/

PyO3 Project. (2026). *Building and distribution*. PyO3 user guide.
https://pyo3.rs/main/building-and-distribution.html

PyO3 Project. (2026). *Features reference*. PyO3 user guide.
https://pyo3.rs/main/features

Rayon Developers. (2026). *ParallelIterator*. Rayon 1.12.0 documentation.
https://docs.rs/rayon/1.12.0/rayon/iter/trait.ParallelIterator.html
