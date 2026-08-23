# RankWeave product/technical gap baseline

Initial status snapshot as of 2026-08-22, with a mitigation-status update on
2026-08-23 (§2). This document exists so a reviewer can answer one question
without re-deriving it from scratch: **what does a buyer of RankWeave still
not get today, and what is already closed?** It is a living document — update
it whenever a §2 row's state changes, a §6 gap closes, or a new gap is found
(see Maintenance below). Do not let it drift from `gh pr list` / `gh issue
list` reality.

## 1. Product identity and responsibility boundary

RankWeave is a **leaf product**: a dependency-free, pure-Python,
standard-library-only library and CLI for hybrid-retrieval score fusion,
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

## 2. Current PR/issue queue (evidence, not aspiration)

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

## 3. LineageWeave reuse-boundary analysis (this session's stated priority)

The request that opened this session asked to find and prioritize
LineageWeave-related PRs. Verification (not assumption) was required first,
per the standing instruction to confirm the actual PR location by
product/responsibility boundary rather than by name:

- Before this document was added, RankWeave contained **zero** references to
  LineageWeave anywhere in the tree, and none of its 3 open PRs or 3 open
  issues mentioned LineageWeave. (This document is necessarily an exception —
  its purpose is the boundary analysis below — so "zero references" describes
  the rest of the tree, not this file.)
- The dependency direction is one-way: **LineageWeave depends on RankWeave**,
  not the reverse. LineageWeave's `lineageweave/rankweave_client.py` fail-closes
  (`RankWeaveNotAvailable`) if the `rankweave` package is missing, and pins
  `rankweave @ git+https://github.com/ContextualWisdomLab/RankWeave.git@61c49c5…`
  — exactly RankWeave's `main` HEAD at session start (commit `61c49c5`, PR #34).
- LineageWeave's ADR 0024 ("Fail-closed RankWeave ranking port") documents the
  consumption contract precisely: `GET /api/rankings` fuses a temporal channel
  and a lexical channel through `weighted_reciprocal_rank_fuse` with
  **Cormack et al. (2009)** `eta=60` and **Samuel et al. (2025)** unequal
  channel weights (temporal 0.25, lexical 0.75). It never invents a score when
  the port is disabled or the package is absent.
- LineageWeave's own 11 open PRs and 19 open issues (re-checked live) contain
  **no** item tagged `rankweave` or `fusion` right now. There was nothing to
  pull into this RankWeave session from that side today.

**Conclusion:** the integration boundary is healthy. There is no orphaned
cross-repo work item. The correct action was to strengthen RankWeave's own
queue and public-contract honesty (§2), not to invent LineageWeave work that
does not exist. **Re-check every loop iteration** — a future RankWeave change
that touches `weighted_reciprocal_rank_fuse`'s signature, `eta` default, or
channel-weight semantics is a breaking change for LineageWeave ADR 0024 and
must be coordinated across both repositories, not merged unilaterally here.

## 4. PRD-lite — buyer-facing capability inventory

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
| Public API stability guarantee for external consumers (LineageWeave, Naruon) | Partially shipped | ADR-level documentation exists (LineageWeave ADR 0024) but RankWeave itself has no versioned public-API-compatibility policy doc (no SemVer contract statement, no deprecation window) |

## 5. TRD-lite — technical contract summary

- **Runtime:** Python 3.10+, standard-library-only, Apache-2.0.
- **Public surface:** `FusionSettings`, `fuse_channel_scores`,
  `weighted_convex_combination_score`, `weighted_convex_fuse`,
  `weighted_reciprocal_rank_fuse`, `evaluate_rankings`, `compare_rankings`,
  `compare_ranking_reports`, `cross_validate_weighted_convex_fusion`,
  `cross_validate_weighted_reciprocal_rank_fusion`,
  `tune_weighted_convex_fusion`, TREC parse/format/compare/compare-family, CLI
  transports, and packaged JSON Schema (v1/v2) report contracts.
- **CLI transport:** `rankweave compare`, `rankweave compare-family`,
  `rankweave verify-artifacts` — bounded (64 MiB/artifact), UTF-8 strict,
  exit-code contract `0`/`1`/`2` (`docs/cli.md`).
- **Governance plane:** `create-release.yml` (verify, read-only) →
  `contents: write` GitHub Release job → isolated `actions: write` dispatch of
  `publish.yml` → OIDC PyPI Trusted Publishing. No stored registry credential
  (`docs/releasing.md`, ADR 0004).

## 6. Gap analysis, prioritized by buyer-felt leverage

Severity: 🔴 blocks a buyer today · 🟡 buyer-visible friction · 🟢 hardening/roadmap.

1. 🔴 **PyPI publication is broken** (issue #35). A buyer who reads the README
   and runs `pip install rankweave` gets `0.1.0`, while the reviewed source
   tree and GitHub Release are `0.18.0` — the published package is missing
   every capability shipped since 0.1.0 (cross-validation, temporal
   backtesting, artifact verification v2, weighted-RRF cross-validation) with
   no version-number relationship between "0.1.0" and "0.18.0" beyond "older
   and newer." This is the single highest-leverage gap: it is not a code gap,
   it is a configuration action blocked outside this repository. **Next action:**
   surface this to whoever holds the PyPI org owner role; nothing further is
   automatable from here.
2. 🟡 **No versioned public-API compatibility policy.** LineageWeave and
   Naruon each pin RankWeave differently (a git commit vs. a PyPI version)
   specifically because there is no documented SemVer/deprecation contract a
   consumer can trust. A buyer integrating a third product would have to read
   source history to know what's safe to upgrade across. **Recommendation:**
   add an ADR stating the public-API surface (§5) is covered by SemVer as of
   a named version, with a minimum deprecation window before removal.
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
5. 🟢 **Rust/GPU computation-layer mandate — deliberately not applied here,
   documented rather than silently skipped.** The org-wide standing
   instruction requires Rust with GPU+CPU multithreading for the computation
   layer of mathematical/psychometrics software. RankWeave's own CLAUDE.md and
   AGENTS.md explicitly and repeatedly require the statistical core to stay
   pure-Python, stdlib-only, with no runtime dependency — a project-level
   instruction that was deliberately authored, reviewed, and merged (it is the
   product's stated identity in §1, not an oversight). RankWeave's workloads
   (paired randomization over ≤16 non-zero differences done exactly; beyond
   that, deterministic local Monte Carlo) are evaluation-time statistics over
   query-count-bounded TREC-style runs, not GPU-scale training or IRT
   estimation — fast-mlsirm (a listed sibling repository) is the
   Rust/GPU-appropriate home for that class of workload. Silently rewriting
   RankWeave's core in Rust would contradict this repository's own governing
   ADRs without a change-controlled decision. **Recommendation, not action
   taken:** if a future profiling run shows the exact/Monte-Carlo comparison
   path is a genuine bottleneck for a real buyer workload, open an ADR
   proposing a narrowly-scoped optional-extension (not a core rewrite) before
   touching this boundary.
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
