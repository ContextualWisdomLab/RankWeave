# Research grounding — RankWeave

RankWeave's defaults, metric conventions, significance comparison, tuning
workflow, interchange contracts, artifact-evidence boundary, and autonomous
delivery controls are tied to published evidence or an authoritative reference
implementation. This directory preserves that grounding with the code.

## Papers

| Source | Grounds |
|---|---|
| Bruch et al. (2024) | Default TM2C2 convex fusion, theoretical normalization, multi-system extension, and sample-efficient offline tuning. |
| Cormack et al. (2009) | Reciprocal rank fusion and the default `eta=60`. |
| Samuel et al. (2025) | Evidence for weighted RRF when retrieval channels have different reliability. |
| Järvelin and Kekäläinen (2002) | Graded cumulative gain, logarithmic rank discounting, and ideal-ranking normalization. |
| Smucker et al. (2007) | Paired topic-level randomization as a suitable transparent test for comparing IR systems. |
| Holm (1979) | Sequentially rejective family-wise error control for candidate-family comparisons. |

Complete APA 7th edition references appear in [References](#references-apa-7th-edition).
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
- **FIPS 180-4** defines SHA-256, which RankWeave uses for exact bounded-input
  byte evidence.
- **JSON Schema Core and Validation Draft 2020-12** define the media type,
  vocabularies, structural assertion keywords, and meta-schema used by the
  packaged report contracts.
- **RFC 8259** requires interoperable JSON exchanged outside a closed ecosystem
  to use UTF-8 and grounds the CLI's locale-independent byte transport.
- **SLSA v1.2 Source Track** covers source authoring, review, and
  source-management threats and grounds the separation between maintainer-owned
  control policy and bounded autonomous product changes.
- **SLSA v1.2 provenance and verification guidance** uses artifact subject
  digests as the verification binding; RankWeave adopts only the narrower
  digest-binding concept and does not claim to emit a SLSA attestation.
- **GitHub Actions OIDC reference** defines the `id-token: write` permission and
  the runner request variables used to obtain a short-lived OIDC token.

## Fusion defaults

Bruch et al. (2024) report that a convex combination of theoretically min-max
normalized scores is robust in and out of domain. RankWeave defaults to
`alpha=0.7`, within the reported stable range, and exposes explicit convex
weights for more than two systems.

RRF remains the rank-only alternative. RankWeave exposes equal-weight and
fixed-weight APIs. The weighted interface is generic and auditable; it does not
reproduce MMMORRF's domain-specific adaptive video estimator (Samuel et al.,
2025).

## Metric conventions

`evaluate_ranking` and `evaluate_rankings` provide precision@k, recall@k,
reciprocal-rank@k, and graded nDCG@k.

RankWeave uses the common exponential nDCG gain `2**relevance - 1`, so its nDCG
is not claimed to be numerically identical to `trec_eval`'s default
identity-gain configuration. Precision uses the requested cutoff denominator,
reciprocal rank is cutoff-bound, and aggregate evaluation requires exact
ranking/judgment query-set parity.

## Paired significance protocol

`compare_ranking_reports` aligns two systems by query identifier, computes
candidate-minus-baseline metric differences, and applies paired Fisher sign
randomization. `compare_rankings` first creates both complete evaluation
reports through the same fail-closed evaluation contract.

The test is grounded in the IR significance-study literature summarized by
Smucker et al. (2007). Their empirical comparison over TREC runs found little
practical difference among randomization, bootstrap, and paired t tests for the
studied measures, while sign and Wilcoxon tests behaved less well. RankWeave
chooses randomization because its paired exchangeability assumption and
calculation can be exposed directly without a numerical dependency.

The operational contract is:

- require identical positive cutoffs and exactly matching unique query IDs;
- align candidate values by query ID, never report position;
- retain every baseline value, candidate value, and difference;
- enumerate all sign assignments for at most 16 non-zero differences;
- otherwise draw deterministic signs from a local `random.Random(seed)`;
- apply the plus-one correction to Monte Carlo p-values;
- expose two-sided and candidate-directed alternatives explicitly;
- never mutate global random state.

A p-value is evidence about the paired null hypothesis, not the magnitude or
commercial importance of the observed effect. Consumers should report the mean
difference and per-query evidence and should keep validation-set policy
selection separate from one-time held-out test comparison.

## Direct TREC comparison composition

`compare_trec_runs` introduces no additional statistical method. It composes
the already grounded contracts in a fixed, auditable order:

1. parse one baseline run and one candidate run with the NIST-derived
   interchange boundary;
2. parse qrels once and preserve negative unjudged entries in the immutable
   artifact;
3. convert each run to decreasing-score rankings;
4. convert qrels to the generic non-negative judgment mapping;
5. delegate both evaluations and paired randomization to `compare_rankings`;
6. retain every parsed artifact, evaluation, and per-query difference in one
   frozen `TrecRunComparisonReport`.

This orchestration prevents benchmark consumers from silently applying a
different parser, query filter, cutoff, score order, or significance option to
one of the two systems. Identical run tags remain permitted because TREC tags
are descriptive provenance fields rather than unique artifact identities.

The complete workflow and interpretation boundary are documented in
[`docs/trec-run-comparison.md`](../trec-run-comparison.md).

## Candidate-family error control

`compare_trec_run_family` reuses one parsed baseline, one parsed qrels artifact,
and one baseline evaluation for an ordered family of candidates. It preserves
every raw paired p-value and applies Holm's sequentially rejective adjustment
(Holm, 1979). The procedure controls the family-wise error rate under arbitrary
dependence, so correlated candidate systems and shared queries do not invalidate
the adjustment.

Candidate families must be defined before inspecting results. Changing the
family after observing p-values changes the statistical question. Adjusted
p-values remain inferential evidence rather than effect size, operational value,
or permission to deploy a winner automatically.

The complete workflow is documented in
[`docs/trec-family-comparison.md`](../trec-family-comparison.md).

## Tuning protocol

`tune_weighted_convex_fusion` and `tune_weighted_reciprocal_rank_fusion`
evaluate caller-defined, insertion-ordered fixed-weight policy families on a
complete judged validation query set. Both support macro nDCG, reciprocal rank,
recall, or precision, preserve every full evaluation, and use candidate order as
the exact tie breaker.

Bruch et al. (2024) report that convex combination can outperform RRF in- and
out-of-domain and can be tuned sample-efficiently. Barata (2026, preprint)
illustrates the stricter experiment boundary adopted here: select a finite
simplex policy only on training queries, distinguish the apparent full-data
optimum from out-of-fold performance, and test marginal fusion value rather than
assuming that a standalone retriever must help a hybrid.

The selected validation policy is not an unbiased final effectiveness estimate.
Consumers must freeze the chosen weights and evaluate them once on an
independent held-out test set before making a production-quality claim.

## Explicit-fold cross-validation protocol

`cross_validate_weighted_convex_fusion` executes caller-defined blocked folds.
Each fold selects a fixed policy on the complementary queries and evaluates that
policy unchanged on held-out queries. It then reconstructs one out-of-fold
ranking map in original query order and separately tunes all judged queries to
recommend a future deployment policy.

Stone (1974) distinguishes cross-validatory choice from assessment. Cawley and
Talbot (2010) show that optimizing a noisy selection criterion can itself
overfit, producing selection bias when model choice and performance assessment
collapse. Roberts et al. (2017) show that random folds can underestimate error
under temporal, spatial, hierarchical, and related dependence and recommend
blocks aligned with the data structure. RankWeave therefore records explicit
caller-owned fold IDs rather than inventing a random split. Barata (2026,
preprint) provides a retrieval-specific example of training-fold weight
selection and held-out fold assessment.

The library cannot prove that a supplied grouping is leakage-safe. Consumers
must keep dependent translations, paraphrases, revisions, synthetic variants,
users, tenants, events, projects, or time windows together when the deployment
question requires it. Symmetric blocked folds are not automatically
rolling-origin forecasting evidence.

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

## Exact input-artifact evidence

Run tags are descriptive and may repeat, so they cannot bind a result to the
exact bytes that were evaluated. RankWeave's opt-in CLI v2 schemas include
SHA-256 and raw byte counts for each baseline run, candidate run, and qrels
artifact.

The bounded reader opens each local file once, requests no more than
`max_input_bytes + 1`, hashes the exact bytes, records their length, and then
strictly decodes the same payload as UTF-8. This makes comments, line endings,
trailing whitespace, and alternate Unicode byte sequences part of artifact
identity even when they do not affect the parsed ranking.

FIPS 180-4 defines the SHA-256 algorithm. SLSA v1.2 provenance represents
subjects with artifact digests and verification compares expected and observed
digests. RankWeave follows that narrow binding pattern, but its JSON report is
not a signed in-toto statement, does not authenticate the producer or build
platform, and does not establish any SLSA build level. Local paths are excluded
because they are mutable, environment-specific, and may reveal sensitive host
structure.

The established v1 schemas remain the default. Artifact evidence requires the
explicit flag and v2 schema identifier so strict consumers never receive a
silent field-set change.

## Machine-readable report contracts

RankWeave packages four strict JSON Schema Draft 2020-12 documents describing
the established pairwise and candidate-family v1/v2 report structures. The
Core specification defines schema identification, references, vocabularies,
and annotation behavior; the Validation specification defines the assertion
keywords used for types, required properties, numeric domains, arrays, enums,
constants, and string patterns.

The schemas set `additionalProperties: false` on report objects and constrain
known metric, alternative, randomization-method, SHA-256, and byte-count
domains. Cross-field invariants such as candidate-count equality, candidate
ordering, and query alignment remain documented with `$comment` because a
portable schema cannot express all domain semantics. RankWeave generation and
statistical APIs continue to enforce those invariants.

Schema validation is a structural compatibility check only. It neither
authenticates a producer, recomputes a digest, proves trusted execution, nor
assesses whether an experimental design supports the reported inference.

## Autonomous source and credential boundaries

The hourly product-development workflow treats model-authored source and tests
as untrusted input. `AGENTS.md`, workflows, security files, ownership policy,
and repository metadata are maintainer-owned source-management controls and are
excluded from autonomous edit permissions and accepted diffs. This boundary is
consistent with the SLSA v1.2 Source Track's focus on authoring, review, and
source-management threats; RankWeave does not claim a SLSA level solely from
these local controls.

After deterministic validation, the workflow rechecks the open-PR queue and
exact base revision before requesting a short-lived OIDC-derived GitHub App
token. It repeats both checks immediately before mutation. GitHub's OIDC
reference establishes the token-request permission and request mechanism; the
two precondition checks are RankWeave's additional single-flight and TOCTOU
controls.

The CLI serializes JSON with `ensure_ascii=False` and writes the resulting bytes
as UTF-8 directly to stdout. This implements RFC 8259's interoperable encoding
requirement independently of locale-specific text-stream encodings.

## References (APA 7th edition)

Bray, T. (Ed.). (2017). *The JavaScript Object Notation (JSON) Data Interchange
Format* (RFC 8259). RFC Editor. https://doi.org/10.17487/RFC8259

Wright, A., Andrews, H., Hutton, B., & Dennis, G. (2022). *JSON Schema: A
media type for describing JSON documents* (Draft 2020-12). JSON Schema.
https://json-schema.org/draft/2020-12/json-schema-core.html

Wright, A., Andrews, H., Hutton, B., & Dennis, G. (2022). *JSON Schema
validation: A vocabulary for structural validation of JSON* (Draft 2020-12).
JSON Schema.
https://json-schema.org/draft/2020-12/json-schema-validation.html

Barata, A. P. (2026). *Do static embeddings add value to hybrid Dutch
retrieval? Cross-validated weighted RRF with paired inference and cross-domain
transfer* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.02112

Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for
hybrid retrieval. *ACM Transactions on Information Systems, 42*(1), Article 20,
1–35. https://doi.org/10.1145/3596512

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model
selection and subsequent selection bias in performance evaluation. *Journal of
Machine Learning Research, 11*, 2079–2107.
https://www.jmlr.org/papers/v11/cawley10a.html

Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion
outperforms Condorcet and individual rank learning methods. In *Proceedings of
the 32nd International ACM SIGIR Conference on Research and Development in
Information Retrieval* (pp. 758–759). Association for Computing Machinery.
https://doi.org/10.1145/1571941.1572114

GitHub. (n.d.). *OpenID Connect reference*. GitHub Docs. Retrieved August 5,
2026, from https://docs.github.com/en/actions/reference/security/oidc

Holm, S. (1979). A simple sequentially rejective multiple test procedure.
*Scandinavian Journal of Statistics, 6*(2), 65–70.
https://doi.org/10.2307/4615733

Järvelin, K., & Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR
techniques. *ACM Transactions on Information Systems, 20*(4), 422–446.
https://doi.org/10.1145/582415.582418

National Institute of Standards and Technology. (2015). *Secure Hash Standard
(SHS)* (FIPS PUB 180-4). U.S. Department of Commerce.
https://doi.org/10.6028/NIST.FIPS.180-4

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J.,
Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B.,
Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F.
(2017). Cross-validation strategies for data with temporal, spatial,
hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929.
https://doi.org/10.1111/ecog.02881

Samuel, S., DeGenaro, D., Guallar-Blasco, J., Sanders, K., Eisape, O.,
Spendlove, T., Reddy, A., Martin, A., Yates, A., Yang, E., Carpenter, C.,
Etter, D., Kayi, E., Wiesner, M., Murray, K., & Kriz, R. (2025). MMMORRF:
Multimodal multilingual modularized reciprocal rank fusion. In *Proceedings of
the 48th International ACM SIGIR Conference on Research and Development in
Information Retrieval* (pp. 4004–4009). Association for Computing Machinery.
https://doi.org/10.1145/3726302.3730157

SLSA Community. (2025). *Supply-chain Levels for Software Artifacts
specification* (Version 1.2). https://slsa.dev/spec/v1.2/

Stone, M. (1974). Cross-validatory choice and assessment of statistical
predictions. *Journal of the Royal Statistical Society: Series B
(Methodological), 36*(2), 111–133.
https://doi.org/10.1111/j.2517-6161.1974.tb00994.x

Smucker, M. D., Allan, J., & Carterette, B. (2007). A comparison of statistical
significance tests for information retrieval evaluation. In *Proceedings of the
Sixteenth ACM Conference on Information and Knowledge Management* (pp. 623–632).
Association for Computing Machinery. https://doi.org/10.1145/1321440.1321528

### Artifact integrity and JSON interoperability

Bray, T. (2017). *The JavaScript Object Notation (JSON) Data Interchange Format* (RFC 8259). RFC Editor. https://doi.org/10.17487/RFC8259

National Institute of Standards and Technology. (2015). *Secure Hash Standard (SHS)* (FIPS PUB 180-4). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.180-4

Supply-chain Levels for Software Artifacts. (n.d.). *Build: Verifying artifacts (SLSA specification v1.2)*. OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts

RFC 8259 says object names should be unique for interoperable interpretation and excludes `NaN` and infinity from JSON numbers. FIPS 180-4 specifies SHA-256 for change detection; NIST has announced a future revision but FIPS 180-4 remains the published standard. SLSA v1.2 verification additionally requires trusted provenance/attestation checks and matching an attestation subject to the artifact digest, so RankWeave's unsigned local comparison makes no SLSA claim.

### Trusted publishing and release provenance

GitHub. (n.d.). *Using artifact attestations to establish provenance for builds*. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Python Packaging Authority. (n.d.). *Publishing with a Trusted Publisher*. PyPI documentation. Retrieved August 5, 2026, from https://docs.pypi.org/trusted-publishers/using-a-publisher/

Trail of Bits. (2023). PEP 740—Index support for digital attestations. *Python Enhancement Proposals*. https://peps.python.org/pep-0740/

Supply-chain Levels for Software Artifacts. (n.d.). *Build: Verifying artifacts (SLSA specification v1.2)*. OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts

PyPI Trusted Publishing exchanges a GitHub OIDC identity for a short-lived publication credential and avoids storing a registry token. PEP 740 index-hosted attestations and GitHub Artifact Attestations bind signed statements to artifact digests in distinct trust systems. Neither proves that retrieval statistics are scientifically valid, that the package is vulnerability-free, or that a buyer's deployment policy has been satisfied.
