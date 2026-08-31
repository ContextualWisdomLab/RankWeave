# ADR 0008: Persistent exact semantic-unit index snapshots

- **Status: Accepted**
- **Date:** 2026-08-31
- **Scope:** exact authorization-scoped ranking over reusable embedding snapshots

## Context

ADR 0007 owns exact semantic-unit cosine and its ordered-input integrity
evidence. Its scalar and packed request forms still validate, hash, transfer,
and score every coordinate on every query. A consumer with 6,578 vectors of
dimension 3,072 therefore submits 161,660,928 vector bytes for each request.
The packed form removes Python scalar expansion but is not an index.

Consumers need a reusable owner-side calculation structure without moving
model selection, database access, or ABAC policy into RankWeave. Approximate
nearest-neighbor structures are not acceptable because their candidate loss
would change recall. Query-result caches are also not acceptable because they
do not bind a result to the exact authorized evidence snapshot.

## Decision

'SemanticUnitExactIndex' builds one immutable snapshot from an opaque snapshot
version, opaque model identity, vector dimension, ordered candidate identities,
and canonical big-endian IEEE 754 binary64 vectors. Build validates the complete
snapshot before it can become active and records separate SHA-256 digests for
the model identity, dimension, exact vectors plus identities, and the combined
snapshot.

The Rust core precomputes each validated candidate vector's maximum-absolute
scale and Euclidean norm and stores its scaled coordinates in one contiguous
array. This is exact index metadata tied to the snapshot digest, not a score
cache. A query:

1. supplies the same opaque model identity, one nonzero finite vector, and the
   complete ordered set of caller-authorized candidate identities;
2. fails closed on a model or dimension mismatch, duplicate authorization, or
   an authorized identity absent from the immutable snapshot;
3. computes every authorized dot product in Rust, with no threshold,
   approximate pruning, candidate window, or dropped coordinate;
4. uses Rayon indexed parallel iteration, preserving each dot product's
   coordinate order and collecting in authorization order so worker count does
   not change scores, ranking, or digests;
5. applies ADR 0007's exact per-item maximum and deterministic tie rules; and
6. returns snapshot evidence, CPU execution profile and observed worker count,
   ordered input digest, output digest, and exact result rows.

'replace_snapshot' first builds and validates a complete replacement outside
the active lock, then swaps one immutable reference atomically. A concurrent
query retains the old snapshot for its whole execution or acquires the new one;
it never observes a mixed snapshot. V1 intentionally has no incremental
mutation API. Consumers recover after restart by loading the same immutable
version and bytes from their governed persistent projection and comparing the
owner-computed digests before activation.

The portable required execution profile is deterministic multithreaded CPU.
RankWeave advertises no GPU profile in v1. A future accelerator requires its own
accepted owner decision, real device execution evidence, and exact or
explicitly bounded parity against the CPU profile; a device label alone is not
evidence.

## Responsibility boundary

- The consumer persists the source projection, selects the model-specific
  snapshot, computes ABAC eligibility, supplies the complete authorized
  candidate identities, and post-authorizes every returned identity.
- RankWeave validates, indexes, and scores only supplied vectors and returns no
  item absent from the caller authorization.
- RankWeave remains store- and provider-agnostic. It does not query a database,
  interpret tenant attributes, select an embedding model, or persist customer
  data.

## Consequences

- Snapshot build and restart recovery remain proportional to all snapshot
  bytes, while a warm query transfers only its vector and authorized opaque
  identities.
- Exact precomputed scales and norms remove repeated decode, validation, and
  norm work. Every authorized coordinate still participates in scoring.
- Rayon adds a lockfile-pinned Rust dependency but no Python runtime
  dependency. Worker count comes from the owner runtime and is reported; it is
  not a ranking parameter.
- Consumers must keep the prior snapshot active or report unavailability when
  replacement validation fails. They may not partially repair a snapshot.

## Rejected alternatives

- **HNSW, IVFFlat, or another approximate index:** can omit a true nearest
  candidate and therefore changes exact recall.
- **Filter after approximate retrieval:** can lose authorized evidence before
  ABAC filtering and cannot prove completeness.
- **Per-query packed full snapshot:** still transfers and scans the full source
  representation on every query.
- **Incrementally mutate v1 in place:** permits mixed model, dimension, and
  vector versions unless a more complex transaction/digest protocol is added.
- **Consumer-owned norms or cosine:** duplicates owner arithmetic and weakens
  the digest boundary.
- **Fixed worker count:** is an ungrounded deployment knob. Indexed parallel
  work is deterministic for every observed worker count.

## References — APA 7th edition

IEEE Computer Society. (2019). *IEEE standard for floating-point arithmetic*
(IEEE Std 754-2019). IEEE. https://doi.org/10.1109/IEEESTD.2019.8766229

National Institute of Standards and Technology. (2015). *Secure Hash Standard
(SHS)* (FIPS PUB 180-4). U.S. Department of Commerce.
https://doi.org/10.6028/NIST.FIPS.180-4

Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text
retrieval. *Information Processing & Management, 24*(5), 513–523.
https://doi.org/10.1016/0306-4573(88)90021-0
