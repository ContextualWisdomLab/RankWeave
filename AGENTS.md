# AGENTS.md — rankweave

Operating guide for automated agents working in this repo.

## What this is

`rankweave` is a **pure-Python, stdlib-only** library for
language-agnostic hybrid-retrieval fusion, effectiveness evaluation, paired
statistical comparison, offline policy tuning, strict TREC interchange, and
direct TREC benchmark comparison, extracted from
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
Context Search under the lab's ONE SOURCE MULTI USE convention
(standalone product *and* submodule-importable).

## Hard rules

- **No dependencies.** The library imports only the Python standard library.
  Do not add a runtime dependency; if you think you need one, the feature
  probably belongs in the consumer, not here.
- **Store-agnostic.** rankweave never talks to a database, embedding provider,
  search index, or benchmark download service. It fuses scores, evaluates and
  compares rankings, selects offline policies, parses interchange artifacts,
  and normalizes query text. Keep SQL, HTTP, and ORM concerns out.
- **Behavior parity with naruon.** A behavior change in shared retrieval
  primitives must be mirrored in naruon's `services/hybrid_retrieval` (and
  vice versa) until naruon consumes this package directly. Prefer additive,
  backward-compatible changes.
- **Permissive license only** (Apache-2.0). Any added code or asset must be
  compatible.
- **Research-grounded defaults, metrics, comparison, and selection.** Numeric
  defaults, metric definitions, significance procedures, gain/discount
  conventions, tuning objectives, and interchange assumptions trace to the
  sources in `docs/research/`. Changing one requires citing evidence and
  updating hand-computed regression tests.
- **Complete evaluation sets.** Aggregate evaluation, comparison, and tuning
  must fail closed when ranking and judgment query IDs differ; omitted queries
  must never silently inflate metrics or significance.
- **Paired comparison is identifier-aligned.** Candidate metric values must be
  joined to baseline values by query identifier, never tuple position. Require
  the same positive cutoff, unique hashable query IDs, and selected metric
  values in `[0, 1]` before testing.
- **Deterministic significance evidence.** Enumerate small paired sign spaces
  exactly. Larger randomization tests use a local seeded `random.Random`, never
  global random state, and retain the seed, draw count, method, alternative,
  observed mean difference, and complete per-query differences.
- **Direct TREC comparison is orchestration only.** Parse each baseline run,
  candidate run, and qrels artifact once; retain all three parsed artifacts;
  convert runs through `TrecRun.rankings_by_query()`; convert qrels through
  `TrecQrels.relevance_by_query()`; and delegate evaluation and significance to
  `compare_rankings`. Never duplicate parser, metric, or randomization logic in
  `trec_comparison.py`.
- **Run tags are evidence, not identity.** Baseline and candidate TREC run tags
  may be identical. Preserve both immutable run artifacts and never infer that
  equal tags imply equal systems or equal source files.
- **Significance is not business value.** Documentation and examples must
  report effect size with the p-value and must not present statistical
  significance as practical significance, independent test performance, or a
  commercial valuation.
- **Validation/test separation.** Tuning selects on validation judgments.
  Documentation and examples must tell consumers to evaluate the selected
  policy once on a separate held-out test set before making a quality claim.
- **Deterministic model selection.** Candidate mapping insertion order is the
  tie-breaker for equal objective values. Never replace it with unordered set
  iteration or nondeterministic parallel reduction.
- **Strict TREC boundaries.** Four-column qrels and six-column run artifacts
  must reject malformed, duplicate, non-finite, or unserializable state before
  evaluation. Qrels relevance is a signed ASCII-decimal integer in
  `[-127, 127]`; portable run tags use 1–20 ASCII letters, digits, periods,
  underscores, or hyphens. Blank and `#` comment lines are ignored without
  losing physical diagnostic line numbers. Run rankings are determined by
  descending score; exact score ties preserve input order as RankWeave's
  documented deterministic extension.
- **Central automation trust boundary.** Repository workflows may call the
  reusable PR-governance workflows only at an immutable central commit SHA.
  Agent-task creation requires a user-to-server `COPILOT_GITHUB_TOKEN`; never
  fall back to the workflow token, and fail closed when the task inventory
  cannot be listed or interpreted.
- **Single-flight autonomous development.** The hourly product loop may start
  a task only when no pull request and no nonterminal Copilot agent task exists.
  Each task must select one bounded buyer-visible gap and open one PR; agents
  never merge their own work or bypass reviews and required checks.
- **Complete quality gates.** Production docstrings and both line and branch
  coverage must remain at 100%.
- **Release metadata stays synchronized.** A release must update
  `pyproject.toml`, `rankweave.__version__`, the expected version test, and
  `CHANGELOG.md` together. The built wheel must preserve `py.typed` and pass
  an isolated installation smoke test.

## Develop

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

## Layout

- `src/rankweave/score_fusion.py` — TM2C2 + per-candidate RRF primitives.
- `src/rankweave/ranked_list_fusion.py` — complete-list score/rank fusion
  with immutable audit results.
- `src/rankweave/evaluation.py` — precision, recall, RR, and graded nDCG
  with immutable per-query and aggregate reports.
- `src/rankweave/comparison.py` — exact and deterministic Monte Carlo paired
  randomization with complete per-query metric evidence.
- `src/rankweave/tuning.py` — deterministic validation-set selection for
  fixed weighted-RRF policies.
- `src/rankweave/trec.py` — strict TREC qrels/run parsing, formatting, and
  direct evaluation adapters.
- `src/rankweave/trec_comparison.py` — thin three-artifact orchestration that
  preserves parsed provenance and delegates to native paired comparison.
- `src/rankweave/query_normalization.py` — NFC query normalization.
- `.github/workflows/hourly-commercialization-loop.yml` — hourly bounded
  review/fix/revalidate/develop orchestration using central reusable policy.
- `docs/operations/hourly-commercialization-loop.md` — setup, credentials,
  single-flight behavior, and failure modes for autonomous maintenance.
- `docs/trec-interoperability.md` — interchange contracts and compatibility
  differences from reference TREC tooling.
- `docs/trec-run-comparison.md` — direct baseline/candidate/qrels comparison
  workflow and preserved audit evidence.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — reviewed product
  design and executable implementation plans.
- `tests/` — behavior tests with hand-computed expected values.
- `docs/research/` — paper, standard, and reference-implementation manifest.
