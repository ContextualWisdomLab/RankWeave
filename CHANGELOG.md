# Changelog

All notable changes to rankweave are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/), and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.7.0] — 2026-08-04

### Added
- `compare_ranking_reports` for fail-closed paired comparison of two complete
  retrieval evaluation reports on exactly matching query identifiers.
- `compare_rankings` for end-to-end evaluation and statistical comparison of
  baseline and candidate ranking maps against one judged query set.
- Immutable `QueryMetricDifference`, `PairedRandomizationResult`, and
  `RankingComparisonReport` records that preserve every aligned per-query
  metric value and the complete significance-test configuration.
- Exact Fisher sign randomization for up to 16 non-zero query differences and
  deterministic plus-one-corrected Monte Carlo randomization above that bound.
- Two-sided, candidate-greater, and candidate-less alternatives for precision,
  recall, reciprocal rank, and graded nDCG at the shared cutoff.

### Changed
- Package metadata and wheel smoke tests now expose and verify the statistical
  comparison API on Python 3.10–3.13.

## [0.6.0] — 2026-08-04

### Added
- Strict four-column TREC qrels and six-column TREC run parsing, canonical
  formatting, immutable audit records, score-ordered ranking conversion, and
  direct evaluation through `evaluate_trec_run`.
- An hourly commercialization workflow that runs the centrally governed
  review/fix/revalidation sequence and starts at most one buyer-visible
  Copilot product task when the PR queue and agent-task queue are both empty.

### Changed
- TREC qrels relevance now follows the reference `trec_eval` interchange
  contract: signed ASCII-decimal integers in `[-127, 127]`. Canonical qrels
  formatting emits integers rather than floating-point spellings.
- TREC parsers ignore blank lines and `#` comment lines while preserving
  physical line numbers in validation errors.
- Portable run tags accept 1–20 ASCII letters, digits, periods, underscores,
  or hyphens, matching NIST submission guidance instead of the earlier
  over-restrictive 1–12 alphanumeric profile.
- TREC public records snapshot iterable inputs and validate tokens, scores,
  ranks, duplicate query/document or rank state, and one consistent run tag
  before they can be serialized.
- TREC rank parsing accepts zero-padded positive ASCII decimal fields while
  preserving their normalized integer value.

## [0.5.0] — 2026-08-03

### Added
- `tune_weighted_reciprocal_rank_fusion` for deterministic offline selection
  of fixed convex weighted-RRF policies on a judged validation query set.
- Immutable `WeightedRRFTuningTrial` and `WeightedRRFTuningReport` records
  containing every candidate policy, complete evaluation evidence, objective
  values, and the selected policy.
- Explicit tuning objectives for macro nDCG, reciprocal rank, recall, and
  precision, with first-candidate deterministic tie-breaking.

## [0.4.0] — 2026-08-03

### Added
- `evaluate_ranking` for precision@k, recall@k, reciprocal-rank@k, and
  exponential-gain nDCG@k over graded relevance judgments.
- `evaluate_rankings` and immutable per-query plus macro evaluation reports,
  with fail-closed query-set matching so accidentally omitted queries cannot
  inflate effectiveness estimates.

## [0.3.0] — 2026-08-03

### Added
- `weighted_reciprocal_rank_fusion_score` and
  `weighted_reciprocal_rank_fuse` for fixed convex channel-reliability
  policies over rank-only retrieval outputs.
- Immutable `FusedWeightedRankedItem` and `WeightedRankContribution`
  records that expose present and missing channel evidence for auditability.

## [0.2.0] — 2026-08-03

### Added
- `weighted_convex_fuse`, immutable `FusedScoredItem` results, and
  `WeightedChannelContribution` audit records for complete normalized-score
  fusion with deterministic tie-breaking.
- `reciprocal_rank_fuse` and immutable `FusedRankedItem` results for
  complete-list RRF with deterministic tie-breaking and per-channel rank
  audit trails.
- `weighted_convex_combination_score` — fuse any number of normalized
  retrieval-channel scores with validated convex weights while preserving
  the existing missing-channel-as-infimum semantics.
- CI gates for 100% line and branch coverage, complete production docstrings,
  and installable wheel smoke tests.

### Fixed
- Validate query text types and require a positive integer normalization
  length cap instead of leaking downstream slicing or Unicode errors.
- Reject booleans and non-real objects for score, weight, bound, rank, and
  RRF-constant inputs with stable `ValueError` contracts.
- Reject `NaN` and infinite scores, bounds, weights, ranks, and RRF
  constants instead of silently clamping or propagating invalid values.
- Enforce the documented `[0, 1]` domain for direct convex fusion and
  require positive integer RRF ranks and constants.

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
