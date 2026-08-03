# Research grounding — RankWeave

RankWeave's defaults, metric conventions, tuning workflow, and interchange
contracts are tied to published evidence or an authoritative reference
implementation. This directory preserves that grounding with the code.

## Papers

| Citation | Grounds |
|---|---|
| Bruch, Gai & Ingber (2023), *An Analysis of Fusion Functions for Hybrid Retrieval*, ACM TOIS 42(1), arXiv:2210.11934 | Default TM2C2 convex fusion, theoretical normalization, multi-system extension, and sample-efficient offline tuning. |
| Cormack, Clarke & Büttcher (2009), *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*, SIGIR 2009 | RRF and the default `eta=60`. |
| Samuel et al. (2025), *MMMORRF: Multimodal Multilingual Modularized Reciprocal Rank Fusion*, SIGIR 2025, DOI: 10.1145/3726302.3730157 | Evidence for weighted RRF when retrieval channels have different reliability. |
| Järvelin & Kekäläinen (2002), *Cumulated Gain-based Evaluation of IR Techniques*, ACM TOIS 20(4), DOI: 10.1145/582415.582418 | Graded cumulative gain, logarithmic rank discounting, and ideal-ranking normalization. |

Where a locally preserved PDF is absent, the source remains cite-only until
redistribution permission is confirmed. Git LFS is intentionally not required.

## Standards and reference implementations

- **Unicode UAX #15** grounds NFC normalization in `normalize_search_text`.
- **NIST `trec_eval`** is the reference implementation for standard qrels and
  run ingestion and for established retrieval-effectiveness measures.
- **NIST TREC qrels guidance** defines the four fields `TOPIC`, `ITERATION`,
  `DOCUMENT`, and `RELEVANCY`.
- **NIST TREC run submission guidance** defines the six fields `topicid`, `Q0`,
  `docid`, `rank`, `score`, and `run-tag`, and documents score-order evaluation.

## Fusion defaults

Bruch, Gai & Ingber report that a convex combination of theoretically min-max
normalized scores is robust in and out of domain. RankWeave defaults to
`alpha=0.7`, within the reported stable range, and exposes explicit convex
weights for more than two systems.

RRF remains the rank-only alternative. RankWeave exposes equal-weight and
fixed-weight APIs. The weighted interface is generic and auditable; it does not
reproduce MMMORRF's domain-specific adaptive video estimator.

## Metric conventions

`evaluate_ranking` and `evaluate_rankings` provide precision@k, recall@k,
reciprocal-rank@k, and graded nDCG@k.

RankWeave uses the common exponential nDCG gain `2**relevance - 1`, so its nDCG
is not claimed to be numerically identical to `trec_eval`'s default
identity-gain configuration. Precision uses the requested cutoff denominator,
reciprocal rank is cutoff-bound, and aggregate evaluation requires exact
ranking/judgment query-set parity.

## Tuning protocol

`tune_weighted_reciprocal_rank_fusion` evaluates named fixed-weight policies on
a complete judged validation query set. It supports macro nDCG, reciprocal
rank, recall, or precision and preserves candidate insertion order as the exact
tie-breaker.

The selected validation policy is not an unbiased final effectiveness
estimate. Consumers must evaluate it once on an independent held-out test set
before making a production-quality claim.

## TREC interchange contract

RankWeave uses the reference formats as the compatibility baseline and applies
additional fail-closed validation for safe service-to-service interchange.

### Qrels

- exactly four content fields;
- relevance is a signed ASCII-decimal integer in `[-127, 127]`, matching the
  `trec_eval` qrels reader's representable judgment contract;
- negative judgments remain in the immutable audit artifact and are omitted
  from the generic non-negative evaluation mapping as explicit unjudged
  markers;
- duplicate query/document judgments are rejected.

### Runs

- exactly six content fields and literal `Q0`;
- positive ASCII-decimal submitted rank and finite score;
- one document and one submitted rank per query;
- one run tag per artifact;
- the portable NIST tag profile of 1–20 ASCII letters, digits, periods,
  underscores, or hyphens.

Both parsers ignore blank lines and lines whose first non-whitespace character
is `#`, while preserving physical line numbers in diagnostics.

TREC evaluation orders results by decreasing score rather than trusting the
submitted rank field. RankWeave preserves source order for exact score ties as
a documented deterministic extension. Exact cross-tool parity should use
distinct scores because reference implementations and track tooling do not all
share the same tie rule.

Public TREC dataclasses enforce the same contracts as text parsing and snapshot
container inputs to immutable tuples. `evaluate_trec_run` then applies the same
exact query-set parity gate as the native evaluation API.

Detailed operational behavior is documented in
[`docs/trec-interoperability.md`](../trec-interoperability.md).
