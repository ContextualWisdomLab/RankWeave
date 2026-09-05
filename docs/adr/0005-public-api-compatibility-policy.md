# ADR 0005: Versioned public-API compatibility policy

- **Status: Proposed** — pending protected integration of PR #41.
- **Date:** 2026-08-22
- **Scope:** the package-root API, installed CLI, and versioned JSON transports

## Context

Two known consumers pin RankWeave differently today, and the difference is a
symptom of a real gap, not a matter of taste. Naruon pins the published
`rankweave==0.1.0` package. LineageWeave pins a specific `main` git commit
(`docs/product-technical-gap-baseline.md` §3; LineageWeave ADR 0024) because
it needs post-0.1.0 APIs (`weighted_reciprocal_rank_fuse` with weighted
channels) that are not on PyPI yet. Neither consumer has a written contract
describing which upgrades are safe, because RankWeave has never published
one. A consumer currently has to read source history to guess.

RankWeave's version is `0.18.0` — pre-1.0 by strict SemVer, where any `0.x`
release is conventionally allowed to break compatibility. That convention is
correct for a package with no real consumers. It is the wrong signal for a
package two other repositories in this organization already import through
`services.hybrid_retrieval`-shaped seams and treat as a stable dependency.

## Decision

1. **The Python package-root surface is exactly `rankweave.__all__`.** Anything reachable
   only through `rankweave.<module>.<name>` and not re-exported at the
   package root is internal and may change without notice. The root
   `__init__.py` docstring and `README.md`'s documented functions are the
   two authoritative, human-readable views of this same set; keep them
   synchronized when `__all__` changes. The installed `rankweave` console
   entry point and its independently versioned pairwise/family JSON schemas
   are additional public transport contracts; they are not Python symbols and
   therefore are frozen by their entry-point and schema-version tests rather
   than by `__all__`.
2. **Effective immediately as of this ADR (source-tree `0.18.0`), names in
   `__all__` are not removed or renamed within a minor version.** A symbol
   present in `__all__` at one published minor version (`0.N.0`) stays
   present, importable, and behaviorally compatible through every patch
   release of that minor version. Removing or renaming a symbol requires a
   minor version bump at minimum, and the removed name must appear in
   `CHANGELOG.md` under a `### Removed` heading naming its replacement, if
   any.
3. **Enforcement is a test, not a promise.** `tests/test_public_api_compatibility.py`
   freezes the exact `__all__` set as of this ADR and asserts every frozen
   name is still exported and still resolvable
   (`hasattr(rankweave, name)`). A PR that breaks this test is either adding
   a genuine removal — which must update the frozen set, the `CHANGELOG.md`
   `### Removed` entry, and this ADR's frozen-set reference together in one
   reviewed change — or it is an accidental regression the test caught
   before a consumer did. New additions to `__all__` do not need to touch
   the frozen set; the test only asserts a lower bound.
4. **Behavioral compatibility, not just import compatibility.** A symbol
   staying importable but silently changing its numeric defaults, gain
   function, `eta`, or channel-weight semantics is still a breaking change
   for LineageWeave ADR 0024, which pins those exact values. Changes to
   defaults documented as research-grounded in `docs/research/README.md`
   require the same minor-version-bump-plus-CHANGELOG discipline as a
   removal, even when the function name is untouched.
5. **This does not commit to PyPI publication cadence.** Issue #35 (PyPI
   Trusted Publisher misconfiguration) is a separate, orthogonal gap. This
   ADR governs what a version *means* once published; it does not promise
   when the next version *will be* published.

## Consequences

A consumer reading this ADR can safely pin `rankweave>=0.18,<0.19` (or the
equivalent commit range) and know that upgrading within that range never
removes a symbol it already imports. A consumer that needs a symbol added
after `0.18.0` still has to pin a specific commit or wait for the next minor
release, exactly as LineageWeave does today — this ADR does not retroactively
publish anything, it only makes the existing informal expectation
enforceable and visible.

Future ADRs that intentionally remove or rename a public symbol must update
`tests/test_public_api_compatibility.py`'s frozen set in the same PR, and
must reference this ADR in their own consequences section.

## Alternatives considered

- **Full SemVer `1.0.0` commitment now:** rejected. A `1.0.0` bump implies a
  stability claim beyond what this ADR makes (it says nothing about numeric
  defaults changing across minor versions, only within them staying put).
  Reaching `1.0.0` is a future decision, not a byproduct of writing this
  policy.
- **No enforcement, policy text only:** rejected. AGENTS.md's own standing
  rule is "write tests before behavior changes"; a compatibility policy with
  no test is a claim nobody checks.
- **Deprecation-warning period before removal:** considered but out of
  scope for this ADR. RankWeave has no runtime warning mechanism today
  (stdlib-only, no logging framework mandated) and no removal has been
  proposed yet to design one against. Add it as a follow-up ADR when a
  concrete removal is proposed, grounded in an actual case instead of a
  hypothetical one.
