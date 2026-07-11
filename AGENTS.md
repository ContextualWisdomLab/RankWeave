# AGENTS.md — rankweave

Operating guide for automated agents working in this repo.

## What this is

`rankweave` is a **pure-Python, stdlib-only** library for
language-agnostic hybrid-retrieval score fusion, extracted unchanged
in behavior from
[ContextualWisdomLab/naruon](https://github.com/ContextualWisdomLab/naruon)
Context Search under the lab's ONE SOURCE MULTI USE convention
(standalone product *and* submodule-importable).

## Hard rules

- **No dependencies.** The library imports only the Python standard
  library. Do not add a runtime dependency; if you think you need one,
  the feature probably belongs in the consumer, not here.
- **Store-agnostic.** rankweave never talks to a database, an
  embedding provider, or a search index. It fuses scores and normalizes
  query text. Keep SQL, HTTP, and ORM concerns out.
- **Behavior parity with naruon.** This is an extraction, not a fork.
  A behavior change here must be mirrored in naruon's
  `services/hybrid_retrieval` (and vice versa) until naruon consumes
  this package directly. Prefer additive, backward-compatible changes.
- **Permissive license only** (Apache-2.0). Any added code or asset must
  be compatible.
- **Research-grounded defaults.** Numeric defaults (alpha=0.7, eta=60,
  the theoretical bounds) trace to the papers in `docs/research/`.
  Changing a default requires citing the evidence.

## Develop

```bash
pip install -e ".[dev]"
python -m pytest -q          # no external services required
python -m ruff check .
```

## Layout

- `src/rankweave/score_fusion.py` — TM2C2 + RRF fusion primitives.
- `src/rankweave/query_normalization.py` — NFC query normalization.
- `tests/` — behavior tests (hand-computed expected values).
- `docs/research/` — paper PDFs + citation manifest.
