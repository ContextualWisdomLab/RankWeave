# RankWeave product/technical gap baseline

The product scope and release acceptance contract are defined in
[`docs/product-requirements.md`](product-requirements.md). This file is the
current evidence ledger; it does not replace the PRD.

Initial status snapshot as of 2026-08-22, with a mitigation-status update on
2026-08-23 (§2). This document exists so a reviewer can answer one question
without re-deriving it from scratch: **what does a RankWeave user still
not get today, and what is already closed?** It is a living document — update
it whenever a §2 row's state changes, a §6 gap closes, or a new gap is found
(see Maintenance below). Do not let it drift from `gh pr list` / `gh issue
list` reality.

### Foundation correction — 2026-09-05, proposed

PR #41 now proposes Rust calculation, semantic ranking/index APIs, native
packaging, and compatibility policy, not only this baseline document. The
tables and queue narrative below retain their explicitly dated historical
snapshot; their old green/approval claims are not current delivery evidence.

The correction source is `cd49e955bfa34d860ee201f7d8ff964bf3b2f569`, which
preserves PR head `eb216beee9abf0adde8d481d9f477d72316ed062` and merges protected
main `92323cb8b55baf5d840cb97fa8534a0e75ef234c` without rewriting history.

- **Portable validation:** the Linux CI failure was reproduced with Rust
  1.97.1 and cargo-llvm-cov 0.8.6 in a credential-free, network-disconnected
  container: 31 tests passed but only 2,858/2,859 regions executed. The missing
  region was the malformed packed-authorization return in the public top-k
  batch API. Its common validation test had been gated to macOS along with
  accelerator-only cases. Splitting those scopes covers the rejection on every
  platform without changing production arithmetic or lowering any threshold.
- **Verification:** Linux now passes 32 Rust tests with 2,939/2,939 regions,
  143/143 functions, and 1,883/1,883 lines. macOS passes 33 tests with
  3,278/3,278 regions, 158/158 functions, and 2,116/2,116 lines. The Python suite
  passes 696 tests; 1,686 statements and 446 branches are covered at 100%.
  Ruff's configured docstring/lint gate, Rust formatting, and Clippy pass.
- **Distinct release identity:** the proposed native APIs now use 0.19.0 in
  Python, Cargo, lock files, and installed CLI checks. A regression first
  rejected the old 0.18.0 source identity. The frozen 0.18.0 public-API set is
  unchanged. Wheel/source archive checks and an isolated installed-wheel
  version/native-import/CLI smoke pass; no tag or package is published here.
- **Current admission contract:** merging PR #64 exposed an obsolete test
  requiring a local hourly cron. Tests and operations documentation now preserve
  central dispatch admission and distinguish separately dispatched review repair
  from the three local jobs. No local schedule was reintroduced.

ADRs 0005–0008 are Proposed until protected integration. Current-head CI,
independent review, dependency-review availability, governed publication, and
consumer-specific upgrade evidence remain required. These tests establish
calculation and packaging contracts, not a held-out quality or p95 improvement.
A generic paired-p95 comparison API is still absent from the released owner
contract; contextual-orchestrator must not duplicate it or consume this open
PR as a released statistical API.

## 1. Product identity and responsibility boundary

RankWeave is a **leaf product**: a Python library and CLI with no third-party
Python runtime dependencies and one packaged Rust calculation core for hybrid-retrieval score fusion,
ranking evaluation, paired/family statistical comparison, offline policy
tuning (including caller-owned blocked-fold cross-validation and
availability-time backtesting), and strict TREC interchange
(ARCHITECTURE.md; AGENTS.md). It must run standalone and be swallowed whole as
a module by a host (Naruon today; LineageWeave as of this session) — the
"hub-and-leaf" composition documented in PR #40's README rewrite is the
supported integration shape, not an MSA violation.

**What RankWeave is *not*:** a database, an embedding provider, a search
index, a benchmark-download service, or an HTTP service. It never calls a
network or a store. Adding any of those belongs in a consumer, not here
(AGENTS.md, "Hard rules").

## 2. Historical PR/issue queue (2026-08-22–23)

Snapshot taken during this session's review→fix→checks→merge pass:

| # | Title | State entering session | Action taken this session |
|---|---|---|---|
| PR #39 | docs: make README operator-first and honest about PyPI | BLOCKED, no review decision | **Closed**, superseded by #40 — same PyPI-honest install fix, broader restructuring |
| PR #40 | Rewrite RankWeave README for customers and operators | BLOCKED, CHANGES_REQUESTED, 2 checks FAILURE (transient GitHub 503 on 2026-08-17 18:17–18:18 UTC) | Fixed the install-order defect and a forward-reference gap (post-0.1.0 API examples above the caveat explaining they need the git install); zero unresolved review threads; all checks green; **blocked only on org-wide review-dispatch throughput (see below)** |
| PR #36 | fix(ci): restore executable hourly governance | BLOCKED, CHANGES_REQUESTED (stale, predating `dismiss_stale_reviews_on_push`) | Verified both issue #37 defects are correctly fixed in-branch; fixed a real doc-structure bug (orphaned heading) found by review; zero unresolved review threads; all checks green; **blocked only on org-wide review-dispatch throughput (see below)** |
| PR #41 | docs: add product/technical gap baseline (this document) | — (opened this session) | Fixed a wording-precision defect found by review; zero unresolved review threads; all checks green; **blocked only on org-wide review-dispatch throughput (see below)** |
| PR #42 | docs: add ADR 0005 versioned public-API compatibility policy | — (opened this session) | Freezes `rankweave.__all__` as of 0.18.0 (§6 gap 2, below), enforced by `tests/test_public_api_compatibility.py`; zero unresolved review threads; all checks green; **blocked only on org-wide review-dispatch throughput (see below)** |
| Issue #38 | Disable orphaned release/PR-repair/hourly-loop workflow identities | Open | **Closed.** Disabled 24 orphaned workflow identities via the Actions API (`PUT .../workflows/{id}/disable`); verified only `ci.yml`, `create-release.yml`, `hourly-commercialization-loop.yml`, `publish.yml` (plus GitHub's own Dependabot/CodeQL dynamic entries) remain active |
| Issue #37 | Fleet automation incident: NVIDIA-before-queue-gate ordering + `secrets: inherit` | Open, fix in PR #36 | Left open pending #36 merge — do not close on a claim, close when the fix actually lands on `main` |
| Issue #35 | PyPI Trusted Publisher misconfigured for v0.18.0 (`invalid-publisher`) | Open | **Blocked-external.** Requires a PyPI project-owner action at `pypi.org/manage/project/rankweave/settings/publishing/` that no repository automation or GitHub API call can perform. Re-verified still blocked; documented here rather than silently dropped, per the standing rule against silently ignoring an external-only blocker. |

### Org-wide review-dispatch throughput bottleneck (discovered this session)

All four RankWeave PRs above reached "zero unresolved threads, all checks
green" during this session but stayed unmergeable because
`ContextualWisdomLab/.github`'s `pr-review-merge-scheduler.yml`
`org-queue-sweep` job enforces **one OpenCode review dispatch per 15-minute
sweep, shared across the entire organization** — not per repository. Evidence
(run `32556682284`, job `96991889320`, 2026-08-22T06:36Z): all three of
RankWeave's ready PRs logged `wait: ... review dispatch limit reached` in the
same sweep that also processed ThreadWeave and EgressWeave. Filed as
[ContextualWisdomLab/.github#1219](https://github.com/ContextualWisdomLab/.github/issues/1219)
with full evidence rather than unilaterally raising a shared, cost-relevant
throttle without visibility into its intended ceiling. This is an
organization-scale gap, not RankWeave-specific — expect it to keep affecting
every repository's merge latency until resolved centrally.

**Mitigation status (updated 2026-08-23):** four independent contributing
causes have since been identified and three merged in
`ContextualWisdomLab/.github`: rotation of the queue-sweep's repo walk order
(#1220, merged) so the shared 1-dispatch/15-minute budget no longer always
starves the same tail of repositories; an `actionlint`
`job.workflow_*`-context bug in a related scheduler workflow (#1221, merged);
a dead GitHub Models fallback chain in `strix.yml` that was blocking checks
with a hallucinated finding (#1226, merged). A fourth fix — rate-limit-aware
retry/defer for the shared GitHub App installation token that the sweep job
itself hits (#1245) — is open but not yet merged pending resolution of an
adversarial-review finding (a per-repo retry cost that can collide with the
sweep job's overall timeout under sustained contention). None of these have
yet flipped RankWeave's own PRs to mergeable as of this update; a separate,
unrelated cause (GitHub Models retirement affecting the review model pool,
`ContextualWisdomLab/.github#624`) may also still be contributing and remains
open.

Re-run before trusting this table stale: `gh pr list --state open` and
`gh issue list --state open` against `ContextualWisdomLab/RankWeave`.

## 3. LineageWeave reuse-boundary analysis

The request that opened this session asked to find and prioritize
LineageWeave-related PRs. Verification (not assumption) was required first,
per the standing instruction to confirm the actual PR location by
product/responsibility boundary rather than by name:

- The dependency direction is one-way: **LineageWeave depends on RankWeave**,
  not the reverse. LineageWeave's `lineageweave/rankweave_client.py` fail-closes
  (`RankWeaveNotAvailable`) if the package is missing.
- LineageWeave ADR 0225 now assigns fusion arithmetic and contribution evidence
  to RankWeave and forbids a second LineageWeave engine. LineageWeave issue
  #338 and PR #663 record the cross-repository consumer boundary.
- RankWeave issue #45 is the active owner work item for a Rust calculation core
  behind the public Python contract. It requires provenance-bearing policies
  and prohibits invented weights, thresholds, candidate windows, folds, and
  missing-channel zeros.
- Existing documented numeric semantics remain research-traceable: Cormack et
  al. (2009) ground RRF and Bruch et al. (2024) ground convex fusion. A paper's
  support for unequal channel reliability does not establish a particular
  consumer weight vector; exact weights require estimator provenance.

**Conclusion:** the product boundary is explicit but not shipped end to end.
RankWeave must publish the Rust-backed owner contract, and each consumer must
upgrade its immutable pin before deleting duplicate arithmetic or claiming the
new engine.

## 4. Capability inventory

| Capability | Status | Evidence |
|---|---|---|
| Fuse scored/rank-only channels (TM2C2 convex, weighted RRF) | Shipped | `score_fusion.py`, `ranked_list_fusion.py`; Bruch et al. (2024), Cormack et al. (2009) |
| Evaluate rankings (precision/recall/RR/nDCG@k) | Shipped | `evaluation.py`; Järvelin & Kekäläinen (2002) |
| Paired statistical comparison with exact/Monte Carlo randomization | Shipped | `comparison.py`; Smucker et al. (2007) |
| Family-wise comparison with Holm correction | Shipped | `trec_family_comparison.py`; Holm (1979) |
| Caller-owned blocked-fold cross-validation (convex + weighted-RRF) | Shipped | `cross_validation.py`; ADR 0002 |
| Availability-time backtesting (no future-leakage) | Shipped | `temporal_backtesting.py`; ADR 0003 |
| Strict TREC interchange (qrels/runs) | Shipped | `trec.py`; NIST TREC guidance |
| Exact-byte artifact verification (opt-in v2 reports) | Shipped | `report_schemas.py`, `docs/artifact-verification.md` |
| Governed, provenance-attested PyPI release | **Broken today** | Issue #35 — Trusted Publisher misconfigured, `0.18.0` unpublished |
| Honest, PyPI-accurate customer README | **In flight** | PR #40 (this session) |
| Public API stability guarantee for external consumers (LineageWeave, Naruon) | Implemented, unreleased | ADR 0005 defines the versioned package-root and CLI transport contracts; `tests/test_public_api_compatibility.py` enforces them. Issue #35 still prevents publishing this source contract for consumers. |

## 5. TRD-lite — technical contract summary

- **Runtime:** Python 3.10+, no third-party Python runtime dependency, one
  packaged Rust calculation core, Apache-2.0.
- **Public surface:** `FusionSettings`, `fuse_channel_scores`,
  `weighted_convex_combination_score`, `weighted_convex_fuse`,
  `weighted_reciprocal_rank_fuse`, `evaluate_rankings`, `compare_rankings`,
  `compare_ranking_reports`, `cross_validate_weighted_convex_fusion`,
  `cross_validate_weighted_reciprocal_rank_fusion`,
  `rank_semantic_units`,
  `tune_weighted_convex_fusion`, TREC parse/format/compare/compare-family, CLI
  transports, and packaged JSON Schema (v1/v2) report contracts.
- **CLI transport:** `rankweave compare`, `rankweave compare-family`,
  `rankweave verify-artifacts` — bounded (64 MiB/artifact), UTF-8 strict,
  exit-code contract `0`/`1`/`2` (`docs/cli.md`).
- **Governance plane:** `create-release.yml` (verify, read-only) →
  `contents: write` GitHub Release job → isolated `actions: write` dispatch of
  `publish.yml` → OIDC PyPI Trusted Publishing. No stored registry credential
  (`docs/releasing.md`, ADR 0004).

## 6. Gap analysis, prioritized by user-visible leverage

Severity: 🔴 blocks a user today · 🟡 user-visible friction · 🟢 hardening/roadmap.

1. 🔴 **PyPI publication is broken** (issue #35). A user who reads the README
   and runs `pip install rankweave` gets `0.1.0`, while the reviewed source
   tree and GitHub Release are `0.18.0` — the published package is missing
   every capability shipped since 0.1.0 (cross-validation, temporal
   backtesting, artifact verification v2, weighted-RRF cross-validation) with
   no version-number relationship between "0.1.0" and "0.18.0" beyond "older
   and newer." This is the single highest-leverage gap: it is not a code gap,
   it is a configuration action blocked outside this repository. **Next action:**
   surface this to whoever holds the PyPI org owner role; nothing further is
   automatable from here.
2. 🟡 **The versioned public-API policy is not released.** ADR 0005 and
   `tests/test_public_api_compatibility.py` now define and enforce the
   package-root and CLI transport compatibility contracts in source. Naruon
   and LineageWeave still cannot consume that work as a published contract
   while issue #35 blocks the next PyPI release. **Recommendation:** publish
   the exact verified release after the external Trusted Publisher
   configuration is repaired; do not represent a source-only commit as an
   available consumer version.
3. 🟡 **Workflow-identity lifecycle has no self-cleaning step** (root cause
   behind issue #38, now remediated once). Every future one-shot
   PR-repair/finalizer workflow will re-accumulate orphaned identities unless
   its own bounded-use teardown calls the disable endpoint. **Recommendation:**
   add a `close-empty`-style final step to the pattern these one-shot
   workflows already follow, or a periodic sweep job, so this doesn't recur
   as a fresh fleet incident every few weeks.
4. 🟢 **Central `pr-review-fix-scheduler.yml` is reachable again.** During
   this session's investigation of PR #36, `ContextualWisdomLab/.github`'s
   `pr-review-fix-scheduler.yml` at a fresh commit was confirmed to exist and
   be resolvable (the old pinned commit `21397126…` is still unreachable —
   201 commits behind, 6 ahead, genuinely diverged — so PR #36's fail-closed
   local hold job remains correct and necessary as-is). Restoring the full
   central repair call with a new reachable pin is a legitimate follow-up,
   but it is new scope requiring its own test-first change per AGENTS.md, not
   something to fold into #36's already-reviewed diff. **Recommendation:**
   file a follow-up issue tracking the re-pin once the central scheduler's
   current commit is confirmed stable, rather than merging it unreviewed
   inside an unrelated PR.
5. 🟡 **The first production fusion primitives are Rust-backed; migration is
   incomplete** (issue #45).
   LineageWeave ADR 0225 names RankWeave as the sole fusion owner, while the
   development head now routes theoretical normalization, two-channel convex
   fusion, and unweighted RRF through `rankweave-core`; N-channel weighted,
   evaluation, comparison, and tuning arithmetic still execute in Python. The
   remaining migration keeps
   the public Python surface as an adapter over one Rust core, preserves
   exact documented semantics, and publishes provenance and limitations with
   every calculation envelope. CPU multithreading and an optional GPU path
   require exact-workload parity and benchmark evidence; no throughput claim
   is available yet. The migration must not add an inferred policy, threshold,
   candidate window, fold, or channel weight.
6. 🟢 **Multilevel/temporal modeling mandate — partially inapplicable, partially
   already shipped.** RankWeave fuses and evaluates rankings; it does not fit
   respondents to latent traits, so the atomistic-fallacy multilevel/
   multiple-membership concern (which governs person-level psychometric
   estimation) does not have a natural target inside this repository — that
   concern belongs to fast-mlsirm/TEPP, which do estimate latent parameters
   from nested data. The **temporal** half of the mandate is already shipped
   here: `temporal_backtesting.py` (ADR 0003) enforces availability-time
   windows and forbids future-leaking assessment queries. No gap to close on
   this axis beyond keeping ADR 0003's guarantees intact.

## 7. UI/UX, Storybook, and accessibility scope note

RankWeave has no frontend application — it is a library and CLI. The
`ui-ux-pro-max` / `anti-ui-slop` / Storybook / e2e-testing instruction from
the parent mandate is scoped here to the only customer-facing "surface" that
exists: README/CLI-output presentation quality and documentation structure
(now addressed for PyPI honesty in PR #40), not a component library. If a
RankWeave-adjacent frontend surface is ever added (unlikely given the leaf
product boundary in §1), this section should be replaced with a real
Storybook inventory, design-token audit, and the full accessibility/
interaction/performance/typography/animation/forms/navigation/charts
checklist from the parent mandate. Until then, forcing that checklist onto a
library with no UI would be inventing scope the product does not have.

## 8. References (APA 7th)

Bruch, S., Nardini, F. M., Rulli, C., & Venturini, R. (2024). Efficient
and effective tree-based and neural learning to rank. *Foundations and Trends
in Information Retrieval*, 17(1), 1–123.

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank
fusion outperforms condorcet and individual rank learning methods. In
*Proceedings of the 32nd international ACM SIGIR conference on Research and
development in information retrieval* (pp. 758–759). ACM.
https://doi.org/10.1145/1571941.1572114

Holm, S. (1979). A simple sequentially rejective multiple test procedure.
*Scandinavian Journal of Statistics*, 6(2), 65–70.

Järvelin, K., & Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR
techniques. *ACM Transactions on Information Systems*, 20(4), 422–446.
https://doi.org/10.1145/582415.582418

Samuel, S., DeGenaro, D., Guallar-Blasco, J., Sanders, K., Eisape, O.,
Spendlove, T., Reddy, A., Martin, A., Yates, A., Yang, E., Carpenter, C.,
Etter, D., Kayi, E., Wiesner, M., Murray, K., & Kriz, R. (2025). MMMORRF:
Multimodal multilingual modularized reciprocal rank fusion. In *Proceedings of
the 48th International ACM SIGIR Conference on Research and Development in
Information Retrieval* (pp. 4004–4009). Association for Computing Machinery.
https://doi.org/10.1145/3726302.3730157

Smucker, M. D., Allan, J., & Carterette, B. (2007). A comparison of
statistical significance tests for information retrieval evaluation. In
*Proceedings of the sixteenth ACM conference on Conference on information and
knowledge management* (pp. 623–632). ACM.
https://doi.org/10.1145/1321440.1321528

Complete references, including standards documents (SLSA v1.2, FIPS 180-4,
RFC 8259, JSON Schema Draft 2020-12), remain in `docs/research/README.md` —
this section does not duplicate that index, only the sources cited directly
in §§3 and 4 above.

## Maintenance

Update this file in the same PR that changes the state of any row in §2, or
in the next PR after a gap in §6 is closed. A stale gap-baseline document is
worse than none — it makes a real product look worse than it is or hides a
real defect behind a claimed fix.
