# Exact report-artifact verification implementation plan

> Execute with test-driven development. Every production branch must be covered,
> and existing report transports must remain unchanged.

## Goal

Add a pure artifact-verification API and an installed CLI workflow that compare
explicit local run and qrels bytes with the digest evidence in RankWeave v2
reports.

## Task 1 — Define the red core contracts

Files:

- create `tests/test_artifact_verification.py`
- create `src/rankweave/artifact_verification.py` initially with public stubs only

Tests:

1. Pairwise v2 evidence produces three ordered verification records.
2. Family v2 evidence preserves candidate order.
3. SHA-256 and byte-count mismatch results remain inspectable.
4. V1 and unknown transports fail closed.
5. Artifact evidence keys and value types are strict.
6. Pairwise and family caller modes are mutually exclusive.
7. Family report, evidence, and caller candidate identifiers align exactly.
8. Public result records are immutable and validate constructor inputs.

Run the focused test and retain the expected failures before implementation.

## Task 2 — Implement the pure verification core

File:

- modify `src/rankweave/artifact_verification.py`

Implementation:

- frozen `ArtifactVerificationRecord`;
- frozen `ArtifactVerificationReport`;
- strict report/evidence parsers;
- exact SHA-256 and byte-count calculation;
- pairwise and family alignment;
- derived verified and mismatch-count properties;
- complete public docstrings;
- no filesystem, JSON parsing, network, database, or provider access.

Run focused tests to green.

## Task 3 — Define CLI red contracts

Files:

- create `tests/test_verify_artifacts_cli.py`
- update existing CLI parser/error tests as needed

Tests:

- `rankweave verify-artifacts` success output and exit `0`;
- mismatch output and exit `1`;
- usage, file, UTF-8, JSON, evidence, and alignment failures exit `2` with no
  stdout;
- pairwise `--candidate-run` and family `--candidate ID=PATH` modes;
- bounded report and artifact reads;
- compact and pretty deterministic JSON;
- path non-disclosure;
- console/module byte parity under an ASCII text locale.

## Task 4 — Implement the CLI adapter

File:

- modify `src/rankweave/cli.py`

Implementation:

- extract one bounded binary-read primitive;
- preserve existing strict text-reader compatibility;
- add `verify-artifacts` arguments;
- parse one strict UTF-8 JSON report;
- read all artifacts exactly once;
- delegate to `verify_report_artifacts`;
- project the immutable result to
  `rankweave.artifact-verification.v1`;
- return `0`, `1`, or `2` according to the design.

Run focused and complete tests.

## Task 5 — Public API and package integration

Files:

- update `src/rankweave/__init__.py`
- update `.github/workflows/ci.yml`

Add public exports and required wheel contents. Add installed-wheel pairwise and
family success and mismatch smoke tests. Verify console/module byte parity and
absence of the development-only validator dependency.

## Task 6 — Release and documentation

Files:

- update `pyproject.toml`
- update `uv.lock`
- update `tests/test_version.py`
- update `CHANGELOG.md`
- update `README.md`
- update `docs/cli.md`
- create `docs/artifact-verification.md`
- update `AGENTS.md`
- update `ARCHITECTURE.md`
- update `CLAUDE.md` if a new permanent contributor rule is required
- update `docs/research/README.md`

Prepare version 0.14.0. Record the current FIPS 180-4 status and SLSA v1.2
verification boundary in APA 7th form. State explicitly that local digest
matching is neither signature nor provenance verification.

## Task 7 — Exact-head verification and merge

Require on one current head:

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --out-dir dist
```

Then require GitHub Python 3.10–3.13, installed-wheel verification smoke,
Security Scan, SAST Semgrep, current-head review status, and zero unresolved
review threads. Merge through protected squash, recheck the open PR queue, and
continue with the next highest-value bounded product gap.
