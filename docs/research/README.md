# Research grounding — rankweave

rankweave's defaults and metric conventions are not arbitrary; each is a
published, empirically supported choice. This directory preserves the source
material and citations so the grounding travels with the code.

## Papers

| File | Citation | License / redistribution |
|---|---|---|
| `pdfs/bruch-gai-ingber-2023-analysis-fusion-functions-hybrid-retrieval.pdf` | Bruch, S., Gai, S., & Ingber, A. (2023). *An Analysis of Fusion Functions for Hybrid Retrieval.* ACM Transactions on Information Systems 42(1). arXiv:2210.11934. | cite-only pending license confirmation |
| `pdfs/cormack-clarke-buettcher-2009-reciprocal-rank-fusion.pdf` | Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods.* SIGIR 2009. | cite-only pending license confirmation |
| — | Samuel, S., et al. (2025). *MMMORRF: Multimodal Multilingual Modularized Reciprocal Rank Fusion.* SIGIR 2025. arXiv:2503.20698. DOI: 10.1145/3726302.3730157. | cite-only; no redistributed copy |
| — | Järvelin, K., & Kekäläinen, J. (2002). *Cumulated Gain-based Evaluation of IR Techniques.* ACM Transactions on Information Systems 20(4), 422–446. DOI: 10.1145/582415.582418. | cite-only; no redistributed copy |

Standards and reference implementations:

- **UAX #15 — Unicode Normalization Forms** (Unicode Consortium), the basis
  for `normalize_search_text`'s NFC step.
- **NIST `trec_eval`**, the standard TREC evaluation implementation and the
  reference for precision-at-cutoff, recall, and first-relevant reciprocal
  rank conventions used by `evaluate_ranking`.

## What each grounds

- **Bruch, Gai & Ingber 2023** → the **default strategy**. TM2C2 (a
  convex combination of *theoretically* min-max normalized scores)
  outperforms Reciprocal Rank Fusion in- and out-of-domain (their
  Tables 2–4); the choice of normalization is immaterial for a convex
  combination (§4.2); `alpha ∈ [0.6, 0.8]` is a robust range needing no
  training data (we default to 0.7). Section 3.1 also notes that much of
  the two-system analysis extends directly to multiple retrieval systems,
  grounding `weighted_convex_combination_score`. Their five desiderata —
  monotonicity, homogeneity, boundedness, Lipschitz continuity, sample
  efficiency — are exactly the properties `convex_combination_score`
  provides and `reciprocal_rank_fusion_score` (a function of ranks,
  not scores) does not.
- **Cormack, Clarke & Büttcher 2009** → the **RRF alternative** and its
  `eta = 60` default.
- **Samuel et al. 2025** → the value of exposing weighted RRF when
  retrieval channels have different reliability. Their video-dependent
  weighting improved MultiVENT 2.0 nDCG@10 from 0.562 with ordinary RRF
  to 0.586 with weighted RRF. RankWeave supplies fixed convex channel
  weights and immutable contribution records; it intentionally does not
  reproduce the paper's domain-specific video weight estimator.
- **Järvelin & Kekäläinen 2002** → graded cumulative gain, logarithmic rank
  discounting, and normalization against an ideal ranking. RankWeave uses
  the common exponential gain variant `2**relevance - 1`, so its nDCG values
  are not asserted to be numerically identical to `trec_eval`'s default
  identity-gain configuration.
- **NIST `trec_eval`** → precision at a requested cutoff uses that cutoff as
  the denominator even when a run is short; recall divides retrieved
  relevant documents by all judged relevant documents; reciprocal rank uses
  the first relevant result and is bounded by the requested cutoff in
  RankWeave's `reciprocal_rank_at_k` implementation.
- **UAX #15** → NFC composition, so decomposed Vietnamese/Korean input
  matches composed indexed text.

## PDF preservation note

Git LFS is intentionally **not** used; PDFs are committed as regular
binaries. Where a PDF is absent, it is because the authoring
environment's network policy blocked the source host (e.g. arxiv.org);
the citation + arXiv id above make the drop mechanical from a
network-allowed session. Only permissively-redistributable PDFs are
committed; others stay cite-only until their license is confirmed.
