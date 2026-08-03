# Changelog

All notable changes to rankweave are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/), and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `weighted_convex_combination_score` — fuse any number of normalized
  retrieval-channel scores with validated convex weights while preserving
  the existing missing-channel-as-infimum semantics.

### Fixed
- Reject `NaN` and infinite scores, bounds, weights, ranks, and RRF
  constants instead of silently clamping or propagating invalid values.

## [0.1.0] — 2026-07-11

Initial extraction from
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
Context Search, unchanged in behavior (ONE SOURCE MULTI USE).

### Added
- `fuse_channel_scores` — fuse one candidate's lexical + dense channel
  evidence into a single bounded score under the selected strategy.
- `FusionSettings` — immutable strategy + parameters (`convex_combination`
  default with `semantic_weight_alpha=0.7`; `reciprocal_rank_fusion`
  with `rank_constant_eta=60`).
- `convex_combination_score`, `reciprocal_rank_fusion_score`,
  `theoretical_min_max_normalize` — the underlying fusion primitives.
- `normalize_search_text` — NFC compose + whitespace-collapse +
  length-cap for the query side of a language-agnostic lexical channel.
- `WORD_SIMILARITY_THEORETICAL_BOUNDS`, `COSINE_DISTANCE_THEORETICAL_BOUNDS`.
- 28 unit tests; no dependencies (stdlib only); typed (`py.typed`).
- Research grounding + paper manifest under `docs/research/`.
