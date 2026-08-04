# TREC candidate-family CLI implementation plan

**Goal:** Expose `compare_trec_run_family` as a versioned, bounded, dependency-free
command-line workflow without duplicating ranking or statistical logic.

**Architecture:** Extend `rankweave.cli` with ordered `ID=PATH` candidate parsing,
a `compare-family` parser, immutable-report projection, and dispatch. Reuse the
existing bounded reader and family comparison API. Keep pairwise behavior and
JSON schema unchanged.

**Technology:** Python 3.10+, argparse, json, pathlib, standard library only.

## Task 1: Define failing CLI contracts

Create `tests/test_cli_family.py` covering successful compact/pretty output,
ordered candidates, Unicode identifiers, projection parity, parser defaults,
invalid alpha, malformed/duplicate specifications, candidate-specific parser
errors, and stderr-only exit status 2 behavior.

Run the focused test file and confirm failure because the family CLI symbols and
subcommand do not yet exist.

## Task 2: Implement ordered candidate parsing and JSON projection

Update `src/rankweave/cli.py` to add:

- `FAMILY_OUTPUT_SCHEMA_VERSION`;
- a finite `(0, 1]` alpha parser;
- ordered `ID=PATH` parsing with printable, trimmed, unique IDs;
- `family_comparison_to_dict`;
- `_run_compare_family`;
- parser options and command dispatch.

Do not duplicate TREC parsing, evaluation, randomization, or Holm correction.
Run the focused test file until green.

## Task 3: Close branch coverage and regression gaps

Add tests for every validation branch, including non-finite alpha, empty IDs or
paths, leading/trailing whitespace, duplicate Unicode IDs, paths containing `=`,
wrong report types, missing candidate files, and malformed candidate run data.
Run the full suite with coverage and retain 100% statements and branches.

## Task 4: Integrate packaging and release metadata

Update:

- `pyproject.toml` to `0.11.0`;
- `src/rankweave/__init__.py` public version;
- `tests/test_version.py` expected version;
- `.github/workflows/ci.yml` installed console/module smoke tests for
  `compare-family`;
- `CHANGELOG.md` with a `0.11.0` release entry.

Build a wheel, install it in an isolated environment, and execute both command
entrypoints outside the source tree.

## Task 5: Document the buyer workflow

Update README, `docs/cli.md`, and `AGENTS.md` with the repeatable candidate
syntax, schema contract, Holm interpretation, resource boundaries, and the rule
that significance alone is not a deployment decision. Keep APA 7th edition
references in `docs/research/README.md`; no new statistical default is added.

## Task 6: Verify and publish through the protected PR loop

Run:

```bash
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

Then create one PR, inspect current-head review threads and Checks, repair every
valid finding, rerun exact-head validation, and squash merge only when repository
policy is satisfied. Confirm the open PR count returns to zero before selecting
the next product gap.
