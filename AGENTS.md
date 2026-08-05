# AGENTS.md — rankweave

Operating guide for automated agents working in this repo.

## What this is

`rankweave` is a **pure-Python, stdlib-only** library and command-line tool for
language-agnostic hybrid-retrieval fusion, effectiveness evaluation, paired and
family-wise statistical comparison, offline policy tuning, strict TREC
interchange, and direct TREC benchmark comparison. It was extracted from
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
Context Search under the lab's ONE SOURCE MULTI USE convention
(standalone product *and* submodule-importable).

## Hard rules

- **No dependencies.** The runtime imports only the Python standard library.
  Do not add a runtime dependency; if you think you need one, the feature
  probably belongs in the consumer, not here.
- **Store-agnostic.** RankWeave never talks to a database, embedding provider,
  search index, or benchmark download service. It fuses scores, evaluates and
  compares rankings, selects offline policies, parses interchange artifacts,
  and normalizes query text. Keep SQL, HTTP, and ORM concerns out.
- **Behavior parity with naruon.** A behavior change in shared retrieval
  primitives must be mirrored in naruon's `services/hybrid_retrieval` until
  naruon consumes this package directly. Prefer additive, backward-compatible
  changes.
- **Permissive license only** (Apache-2.0). Any added code or asset must be
  compatible.
- **Research-grounded defaults, metrics, comparison, and selection.** Numeric
  defaults, metric definitions, significance procedures, gain/discount
  conventions, tuning objectives, and interchange assumptions trace to the
  APA 7th edition references in `docs/research/`. Changing one requires
  evidence and hand-checked regression tests.
- **Complete evaluation sets.** Aggregate evaluation, comparison, and tuning
  fail closed when ranking and judgment query IDs differ; omitted queries must
  never silently inflate metrics or significance.
- **Paired comparison is identifier-aligned.** Candidate metric values join to
  baseline values by query identifier, never tuple position. Require the same
  positive cutoff, unique hashable query IDs, and selected metric values in
  `[0, 1]`.
- **Deterministic significance evidence.** Enumerate small paired sign spaces
  exactly. Larger tests use a local seeded `random.Random`, never global random
  state, and retain the seed, draw count, method, alternative, mean difference,
  and complete per-query differences.
- **Family-wise comparison reuses one baseline.** Parse and evaluate the shared
  baseline and qrels exactly once. Each named candidate delegates to
  `compare_ranking_reports` with the same explicit options. Never duplicate
  parser, metric, or randomization logic in `trec_family_comparison.py`.
- **Holm adjustment is ordered and auditable.** Sort by raw p-value and original
  candidate index, multiply by remaining family size, cap at one, enforce
  monotonicity with a cumulative maximum, and map adjusted values back to input
  order. Preserve raw and adjusted p-values plus the alpha decision.
- **The candidate family is explicit.** Candidate mapping insertion order is
  stable audit evidence. Candidate IDs must be hashable and unique. Run tags
  are provenance fields, not candidate identity, and may repeat.
- **Direct TREC comparison is orchestration only.** Parse each baseline run,
  candidate run, and qrels artifact once; retain parsed artifacts; convert runs
  through `rankings_by_query`; convert qrels through `relevance_by_query`; and
  delegate to native comparison APIs.
- **The CLI is an adapter, not a second engine.** `rankweave compare` delegates
  to `compare_trec_runs`, and `rankweave compare-family` delegates to
  `compare_trec_run_family`. Do not duplicate parsing, metric, query-alignment,
  randomization, or Holm logic in `cli.py`.
- **CLI families are explicit and ordered.** Parse repeatable `--candidate
  ID=PATH` inputs in command-line order. Reject empty, duplicate, non-printable,
  `=`-containing, or whitespace-padded candidate IDs. Never scan a directory or
  use an unordered collection to define the statistical family.
- **CLI transport is stable.** Success writes exactly one versioned UTF-8 JSON
  document and a newline to the standard-output byte stream with exit `0`,
  independent of the process locale. Expected usage, file, UTF-8, size, TREC,
  evaluation, and statistical errors write one stderr line, no stdout, and exit
  `2`. Pairwise and family schemas are independently versioned.
- **Artifact provenance is opt-in and exact.** Default CLI output must remain the
  exact v1 contract. `--include-artifact-digests` emits only the corresponding
  v2 schema. Hash the same bounded raw bytes that are later decoded, record raw
  byte counts, preserve candidate order, and never emit local paths. A SHA-256
  digest is an integrity binding, not a signature, producer authentication,
  trusted-execution proof, or SLSA-level claim.
- **Report schemas are public compatibility contracts.** The packaged Draft
  2020-12 resources must describe every emitted pairwise and family v1/v2
  document exactly. Keep all objects strict, preserve stable resource discovery
  order, validate real generated reports in development tests, and verify every
  resource from an installed wheel. Do not add a runtime validator dependency.
- **CLI input is bounded.** Every artifact read requests no more than
  `max_input_bytes + 1`. Never replace it with `read()`, `read_bytes()`, or any
  other unbounded operation after a size check. The limit applies separately to
  the baseline, qrels, and every candidate artifact. Digest mode must not cause
  a second file read.
- **Significance is not business value.** Documentation reports effect size
  with raw or adjusted p-values and never presents statistical significance as
  practical significance, independent test performance, or valuation.
- **Validation/test separation.** Tuning selects on validation judgments.
  Evaluate selected policies once on a separate held-out test set before a
  final quality claim.
- **Deterministic model selection.** Candidate mapping insertion order is the
  tie-breaker for equal objective values. Do not replace it with unordered set
  iteration or nondeterministic reduction.
- **Strict TREC boundaries.** Four-column qrels and six-column run artifacts
  reject malformed, duplicate, non-finite, or unserializable state. Qrels
  relevance is a signed ASCII-decimal integer in `[-127, 127]`; portable run
  tags use 1–20 ASCII letters, digits, periods, underscores, or hyphens. Blank
  and `#` comment lines are ignored without losing physical line numbers. Run
  rankings use descending score; exact score ties preserve input order.
- **Central automation trust boundary.** Repository workflows call reusable
  PR-governance workflows only at immutable central commit SHAs. The hourly
  product-development stage uses a hash-pinned OpenCode binary and the official
  built-in NVIDIA provider; do not replace either with an unpinned installer,
  moving branch, or dynamically selected custom provider package.
- **Agent-control policy is maintainer-owned.** `AGENTS.md` is a reviewed
  agent-control file. Autonomous product authoring must deny it in OpenCode edit
  permissions and in the deterministic diff gate; only an explicit maintainer
  PR may change this file.
- **Provider credentials are narrowly scoped.** `NVIDIA_NIM_API_KEY` may appear
  only in the eligibility gate and static OpenCode authoring steps. No provider
  key, GitHub token, or OIDC request token may be present in a process that
  executes model-authored Python.
- **Autonomous tools are non-executing.** OpenCode authoring phases deny Bash,
  web access, external directories, LSP, subagents, skills, and questions. The
  model may edit bounded repository files; deterministic workflow steps alone
  execute tests, build artifacts, create branches, and open PRs.
- **Autonomous TDD is evidence-backed.** The first phase may edit only tests and
  design specifications. A network-isolated, sanitized pytest process must
  produce a genuine failed test before production edits are allowed.
- **Autonomous diffs are bounded.** Never permit generated changes to workflow,
  ownership, security, environment, Git-submodule, binary, symlink, or agent
  control files. Enforce changed-file count, per-file bytes, aggregate bytes,
  text-only content, and at least one production Python change.
- **Untrusted validation is sandboxed.** Execute model-authored code with no
  network, `env -i`, an isolated PID namespace, and a fresh `/proc`. Record and
  compare workspace manifests so tests or imports cannot rewrite the proposal.
- **Single-flight autonomous development.** The hourly product loop starts only
  after central governance succeeds and no PR is open. Recheck the open-PR queue
  and exact base SHA before requesting the short-lived OIDC-derived mutation
  token, then repeat both checks immediately before opening the PR. Open one PR
  only; never approve, merge, publish, release, rebase, or hide a stale generated
  proposal.
- **Complete quality gates.** Production docstrings and both line and branch
  coverage remain at 100%.
- **Release metadata stays synchronized.** A release updates `pyproject.toml`,
  `rankweave.__version__`, the expected version test, and `CHANGELOG.md`
  together. The wheel preserves `py.typed`, the CLI modules, and the installed
  console script, and passes isolated installation smoke tests for both console
  and module entrypoints, including every new schema mode.

## Develop

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

## Layout

- `src/rankweave/score_fusion.py` — TM2C2 and scalar RRF primitives.
- `src/rankweave/ranked_list_fusion.py` — complete-list fusion and audit data.
- `src/rankweave/evaluation.py` — precision, recall, RR, and graded nDCG.
- `src/rankweave/comparison.py` — exact and Monte Carlo paired randomization.
- `src/rankweave/tuning.py` — validation-set weighted-RRF policy selection.
- `src/rankweave/trec.py` — strict TREC parsing, formatting, and evaluation.
- `src/rankweave/trec_comparison.py` — direct three-artifact paired comparison.
- `src/rankweave/trec_family_comparison.py` — named candidate-family
  comparison with Holm family-wise correction.
- `src/rankweave/cli.py` — bounded pairwise/family input, v1/v2 JSON
  projection, exact artifact evidence, and exit contracts.
- `src/rankweave/report_schemas.py` — stable schema discovery and package-resource loading.
- `src/rankweave/schemas/` — strict Draft 2020-12 report contracts shipped in the wheel.
- `src/rankweave/__main__.py` — module entrypoint only.
- `src/rankweave/query_normalization.py` — NFC query normalization.
- `.github/workflows/hourly-commercialization-loop.yml` — hourly governed
  review/fix/revalidate/develop orchestration.
- `docs/operations/hourly-commercialization-loop.md` — automation setup and
  failure modes.
- `docs/trec-interoperability.md` — interchange contracts.
- `docs/trec-run-comparison.md` — direct pairwise TREC workflow.
- `docs/trec-family-comparison.md` — candidate-family and Holm workflow.
- `docs/cli.md` — installed commands, report transports, artifact verification,
  and operator boundaries.
- `docs/report-schemas.md` — machine-readable schema discovery, validation,
  compatibility, and interpretation boundaries.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — reviewed designs
  and executable implementation plans.
- `tests/` — hand-computed behavior and contract tests.
- `docs/research/` — APA 7th edition paper, standard, and reference manifest.

## Code-owner review gates — disabled (on hold)

As of 2026-08-04, code-owner review requirements
(`require_code_owner_reviews` in branch protection and
`require_code_owner_review` in rulesets) are disabled across the
ContextualWisdomLab organization. The organization currently has one maintainer,
so a code-owner approval gate cannot be satisfied. Do not re-enable these
settings or add CODEOWNERS-based merge gates until multiple maintainers exist.

## RankWeave 0.14 verification gate

Changes to artifact verification must preserve raw-byte hashing, independent digest and byte-count comparison, exact family order, path/payload non-disclosure, strict persisted JSON, console/module parity, the packaged verification schema, and 100% production statement and branch coverage. Do not describe a digest match as authentication, attestation, provenance verification, or a SLSA level.
