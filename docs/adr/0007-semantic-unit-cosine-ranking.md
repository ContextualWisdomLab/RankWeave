# ADR 0007: Rust-owned semantic-unit cosine ranking

- **Status: Accepted**
- **Date:** 2026-08-26
- **Scope:** ranking caller-authorized embedding vectors by semantic unit

## Context

Consumers need to compare one query embedding with paragraph-, DOM-, or image
region-level embeddings without copying vector arithmetic into each product.
RankWeave owns retrieval-ranking calculation, while the consumer still owns
source access and authorization and contextual-orchestrator owns embedding
model discovery and execution. ADR 0006 requires migrated arithmetic to have
one Rust implementation behind the Python contract.

Cosine is undefined for a zero vector. Ragged or non-finite vectors do not
describe one valid vector space. Neither case may be repaired by padding,
dropping coordinates, inventing a fallback score, or choosing another model.

## Decision

`rank_semantic_units` accepts one already-authorized query vector and an
ordered sequence of `(item_id, unit_id, vector)` candidates. The Rust core:

1. rejects empty, non-finite, zero-norm, dimension-mismatched, and duplicate
   item/unit inputs with stable error codes;
2. computes cosine in caller coordinate order, scaling each vector by its
   maximum absolute component before the dot product and norms to avoid finite
   square overflow;
3. clamps raw cosine to `[0, 1]` without remapping `[-1, 1]`, adding a weight,
   or applying a relevance threshold;
4. retains the highest-scoring unit for each item, breaking an exact unit tie
   by ascending `unit_id`;
5. orders items by descending score and then ascending `item_id`; and
6. returns the winning unit, score, vector dimension, schema and algorithm
   versions, and a SHA-256 digest of a canonical length-prefixed encoding of
   the exact ordered query and candidates.

The digest binds UTF-8 identifiers and IEEE 754 binary64 bit patterns. It is
integrity evidence only, not authentication, provenance, or scientific
validity. The Python module is a typed record/transport adapter and contains no
second cosine implementation.

## Responsibility boundary

- The caller filters and authorizes candidates before the call and
  post-authorizes returned opaque identifiers.
- contextual-orchestrator selects the embedding provider and model and returns
  vectors plus model provenance.
- RankWeave validates and ranks supplied vectors. It does not call a provider,
  select a model, query a store, infer a cutoff, or apply a business threshold.

## Consequences

- Consumers can delete local cosine and per-item max-pooling arithmetic after
  they pin a released RankWeave artifact containing this contract.
- Negative cosine is represented by the documented channel infimum `0`, not a
  manufactured positive score.
- Identifier lexical order is now public tie evidence; callers needing another
  order must supply it as a separate downstream presentation policy.
- SHA-256 adds one small, lockfile-pinned Rust dependency; no Python runtime
  dependency is added.

## Rejected alternatives

- **Keep cosine in each consumer:** duplicates the calculation and versioning
  boundary that ADR 0006 removes.
- **Pad ragged vectors or treat zero norm as zero similarity:** fabricates a
  valid comparison from invalid vector-space evidence.
- **Map cosine from `[-1, 1]` to `[0, 1]`:** changes raw embedding similarity
  and creates a positive score for orthogonal or opposing evidence.
- **Select the model or authorization policy here:** crosses the provider and
  consumer trust boundaries.

## References — APA 7th edition

IEEE Computer Society. (2019). *IEEE standard for floating-point arithmetic*
(IEEE Std 754-2019). IEEE. https://doi.org/10.1109/IEEESTD.2019.8766229

National Institute of Standards and Technology. (2015). *Secure Hash Standard
(SHS)* (FIPS PUB 180-4). U.S. Department of Commerce.
https://doi.org/10.6028/NIST.FIPS.180-4

Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text
retrieval. *Information Processing & Management, 24*(5), 513–523.
https://doi.org/10.1016/0306-4573(88)90021-0
