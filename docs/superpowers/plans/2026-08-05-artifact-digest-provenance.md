# Artifact-digest provenance implementation plan

> Execute with test-driven development. Every implementation step follows a
> failing contract test and must preserve 100% production statement and branch
> coverage.

## Goal

Add opt-in SHA-256 and byte-count evidence for every CLI input artifact without
changing the established v1 JSON contracts.

## Task 1 — Define red transport contracts

Files:

- create `tests/test_cli_artifact_digests.py`
- update `tests/test_cli.py`
- update `tests/test_cli_family.py`

Tests:

1. `--include-artifact-digests` is accepted by pairwise and family commands.
2. Pairwise digest mode emits `rankweave.trec-comparison.v2` and exact SHA-256
   plus byte counts for baseline, candidate, and qrels.
3. Family digest mode emits `rankweave.trec-family-comparison.v2` and ordered
   candidate digest evidence.
4. Default output remains v1 with its exact field order and no `artifacts` key.
5. Local paths never appear in digest-mode JSON.
6. Unicode byte count differs from character count and hashes exact UTF-8 bytes.
7. A raw-byte-only change changes the digest even when evaluation is unchanged.
8. Console and module entrypoints emit byte-identical v2 JSON.

Run the focused tests and retain the expected missing-option/schema failures.

## Task 2 — Implement bounded artifact evidence

File:

- modify `src/rankweave/cli.py`

Implementation:

1. Add a frozen internal bounded-text artifact dataclass containing `text`,
   `sha256`, and `byte_count`.
2. Refactor the bounded reader to read once, hash exact bytes, count exact
   bytes, and decode the same payload as strict UTF-8.
3. Keep `read_text_bounded` as a compatibility wrapper returning `.text`.
4. Add immutable internal pairwise and family digest evidence records.
5. Add v2 schema constants and the shared CLI flag.
6. Extend projection functions so `None` retains v1 exactly and supplied
   evidence emits v2.
7. Keep paths out of every projection.

Run focused tests until green.

## Task 3 — Close validation and coverage branches

Files:

- update `tests/test_cli_artifact_digests.py`
- update existing CLI tests where necessary

Cover:

- wrong digest evidence type;
- candidate identifier/order mismatch;
- missing or extra family evidence;
- internal record validation if exposed through projection helpers;
- v1/v2 projection type guards;
- exact raw-byte hashing and byte-count boundaries.

Run Ruff, the complete suite, and coverage. Production statement and branch
coverage must remain 100%.

## Task 4 — Package and operator integration

Files:

- update `.github/workflows/ci.yml`
- update `README.md`
- update `docs/cli.md`
- update `AGENTS.md`

Add installed-wheel console and module smoke tests for pairwise and family v2.
Document opt-in behavior, field order, path non-disclosure, digest limitations,
and verification examples.

## Task 5 — Research and release metadata

Files:

- update `docs/research/README.md`
- update `CHANGELOG.md`
- update `pyproject.toml`
- update `src/rankweave/__init__.py`
- update `tests/test_version.py`

Record FIPS 180-4 and SLSA v1.2 references in APA 7th edition. State clearly
that digest evidence is not a signature or SLSA-level claim. Prepare version
0.12.0 and keep all version surfaces synchronized.

## Task 6 — Exact-head verification and merge

Run and require:

```bash
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

Then require GitHub Python 3.10–3.13, package smoke, Security Scan, SAST Semgrep,
current-head review, and zero unresolved review threads. Merge through protected
squash only. Recheck the open-PR queue immediately after merge.
