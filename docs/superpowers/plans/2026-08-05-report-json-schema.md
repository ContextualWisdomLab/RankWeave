# Versioned report JSON Schema implementation plan

> Execute with TDD. Production statement and branch coverage remain 100%.

## Goal

Ship strict Draft 2020-12 schemas for every RankWeave report transport and make
them discoverable from Python, shell, CI, containers, and MSA consumers without
adding a runtime dependency.

## Task 1 — Define failing schema-resource contracts

Files:

- create `tests/test_report_schemas.py`
- create `tests/test_schema_cli.py`

Tests:

1. Import `ReportSchemaDescriptor`, `available_report_schemas`,
   `load_report_schema_text`, and `load_report_schema` from `rankweave`.
2. Require four descriptors in stable order.
3. Require fresh parsed dictionaries and exact trailing-newline text.
4. Reject unsupported report types and versions with stable `ValueError`.
5. Require `rankweave schema --report-type ... --schema-version ...` and the
   equivalent module entrypoint to emit identical UTF-8 bytes.
6. Require stderr-only exit-2 usage failures.

Run focused tests and retain the expected import/subcommand failures.

## Task 2 — Add strict packaged schemas

Files:

- create `src/rankweave/schemas/__init__.py`
- create four `*.schema.json` resources
- create `src/rankweave/report_schemas.py`

Implementation:

1. Add frozen descriptor records and a fixed descriptor registry.
2. Use `importlib.resources.files` to load wheel resources.
3. Return canonical text with one trailing newline.
4. Return a fresh dictionary from each parsed load.
5. Include Draft 2020-12 `$schema`, stable URN `$id`, strict required fields,
   `additionalProperties: false`, reusable `$defs`, numeric bounds, enums, and
   v2 digest constraints.
6. Document non-expressible cross-field invariants through `$comment`.

## Task 3 — Validate real RankWeave reports

Files:

- update `tests/test_report_schemas.py`

Development dependency:

- add `jsonschema>=4.23,<5` to `[project.optional-dependencies].dev`

Tests:

1. Check all four schemas with `Draft202012Validator.check_schema`.
2. Generate real pairwise and family v1/v2 reports using CLI execution.
3. Validate each report against the matching packaged schema.
4. Mutate representative documents to prove rejection of missing/extra fields,
   invalid enums, malformed SHA-256, and negative byte counts.
5. Cover every public validation and resource-loading branch.

## Task 4 — Add the schema CLI

Files:

- modify `src/rankweave/cli.py`
- update `tests/test_schema_cli.py`

Implementation:

1. Add a `schema` subcommand with required report type and schema version.
2. Return canonical packaged schema text rather than reserializing it.
3. Preserve UTF-8 byte output and stable exit status behavior.
4. Keep pairwise/family execution unchanged.

## Task 5 — Package and installed-environment verification

Files:

- update `.github/workflows/ci.yml`

Verification:

1. Require every schema resource inside the wheel.
2. Install the wheel in a clean environment outside the source tree.
3. Load all four schemas from the installed package.
4. Compare console and module schema output byte-for-byte.
5. Validate installed CLI v1/v2 reports with the installed schema resources.

## Task 6 — Documentation and release

Files:

- update `README.md`
- update `docs/cli.md`
- update `AGENTS.md`
- update `docs/research/README.md`
- update `CHANGELOG.md`
- update `pyproject.toml`
- update `src/rankweave/__init__.py`
- update `tests/test_version.py`

Document JSON Schema Core and Validation Draft 2020-12 in APA 7th edition form.
State that structural validation is not authenticity, digest verification,
trusted execution, or scientific validity. Prepare RankWeave 0.13.0.

## Task 7 — Exact-head review and merge

Require:

```bash
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

Then require Python 3.10-3.13, package smoke, Security Scan, SAST Semgrep,
current-head review, and zero unresolved review threads. Merge through protected
squash and immediately recheck the open-PR queue.
