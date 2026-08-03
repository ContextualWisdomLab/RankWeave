# AGENTS.md — rankweave

Operating guide for automated agents working in this repo.

## What this is

`rankweave` is a **pure-Python, stdlib-only** library for
language-agnostic hybrid-retrieval fusion, effectiveness evaluation, and
offline policy tuning, extracted from
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
Context Search under the lab's ONE SOURCE MULTI USE convention
(standalone product *and* submodule-importable).

## Hard rules

- **No dependencies.** The library imports only the Python standard library.
  Do not add a runtime dependency; if you think you need one, the feature
  probably belongs in the consumer, not here.
- **Store-agnostic.** rankweave never talks to a database, embedding provider,
  or search index. It fuses scores, evaluates rankings, selects offline
  policies, and normalizes query text. Keep SQL, HTTP, and ORM concerns out.
- **Behavior parity with naruon.** A behavior change in shared retrieval
  primitives must be mirrored in naruon's `services/hybrid_retrieval` (and
  vice versa) until naruon consumes this package directly. Prefer additive,
  backward-compatible changes.
- **Permissive license only** (Apache-2.0). Any added code or asset must be
  compatible.
- **Research-grounded defaults, metrics, and selection.** Numeric defaults,
  metric definitions, gain/discount conventions, and tuning objectives trace
  to the papers in `docs/research/`. Changing one requires citing evidence and
  updating hand-computed regression tests.
- **Complete evaluation sets.** Aggregate evaluation and tuning must fail
  closed when ranking and judgment query IDs differ; omitted queries must
  never silently inflate metrics.
- **Validation/test separation.** Tuning selects on validation judgments.
  Documentation and examples must tell consumers to evaluate the selected
  policy once on a separate held-out test set before making a quality claim.
- **Deterministic model selection.** Candidate mapping insertion order is the
  tie-breaker for equal objective values. Never replace it with unordered set
  iteration or nondeterministic parallel reduction.
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
- `src/rankweave/tuning.py` — deterministic validation-set selection for
  fixed weighted-RRF policies.
- `src/rankweave/query_normalization.py` — NFC query normalization.
- `tests/` — behavior tests with hand-computed expected values.
- `docs/research/` — paper PDFs + citation manifest.
