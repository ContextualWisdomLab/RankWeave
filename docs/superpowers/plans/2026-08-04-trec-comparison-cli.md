# TREC Comparison CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make strict baseline-versus-candidate TREC comparison available as a
stable shell command that emits one versioned JSON audit document.

**Architecture:** Add one focused `cli.py` adapter that validates command-line
options, performs bounded strict-UTF-8 file reads, delegates all retrieval and
statistical behavior to `compare_trec_runs`, and projects the immutable result
to JSON. Add a trivial `__main__.py` entrypoint and one console-script mapping.

**Tech Stack:** Python 3.10+, standard-library `argparse`, `json`, `pathlib`,
pytest, coverage, Ruff, Hatchling.

## Global Constraints

- No runtime dependencies.
- Python 3.10–3.13 compatibility.
- No duplicated TREC, evaluation, or comparison algorithms.
- Maximum 64 MiB per artifact by default, with a pre-read size check and an
  actual read bounded to `max_input_bytes + 1`.
- Strict UTF-8 input.
- JSON to stdout only; errors to stderr only.
- Exit 0 on success and 2 for expected user/input failures.
- 100% production line and branch coverage and complete docstrings.
- Package, documentation, version, and wheel smoke tests stay synchronized.

---

### Task 1: Write failing CLI behavior tests

**Files:**
- Create: `tests/test_cli.py`
- Create: `tests/test_module_entrypoint.py`

**Interfaces:**
- Expects `rankweave.cli.main`, `build_parser`, `comparison_to_dict`, and
  `read_text_bounded`.
- Expects `python -m rankweave` to dispatch to the same `main` function.

- [x] Create temp baseline/candidate/qrels files and assert compact JSON,
  schema version, fixed field order, Unicode query IDs, and trailing newline.
- [x] Assert `--pretty` output and all explicit statistical options.
- [x] Assert missing file, directory, invalid UTF-8, oversize, malformed TREC,
  invalid positive integers, and unsupported choice errors return 2, emit no
  stdout, and write the stable stderr prefix.
- [x] Simulate post-stat growth to exercise the bounded after-read size gate.
- [x] Exercise module entrypoint behavior.
- [x] Run focused tests and observe the expected missing-module failure.
- [x] Commit the red tests.

### Task 2: Implement parser, bounded reads, and error contract

**Files:**
- Create: `src/rankweave/cli.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_contracts.py`

**Interfaces:**
- Produces `build_parser() -> argparse.ArgumentParser`.
- Produces `read_text_bounded(path, max_input_bytes) -> str`.
- Produces `main(argv=None) -> int`.

- [x] Subclass `ArgumentParser.error` to raise an internal usage exception.
- [x] Add the `compare` subcommand and documented arguments/defaults.
- [x] Parse positive decimal integers and signed seeds with stable errors.
- [x] Read at most `max_input_bytes + 1` bytes after the pre-read size check and
  decode strict UTF-8.
- [x] Add a regression test that first failed because the original reader used
  `read(-1)`, then pin the explicit bounded read request.
- [x] Catch expected usage, I/O, Unicode, and `ValueError` failures, print one
  prefixed line to stderr, and return 2.
- [x] Run focused parser/read/error tests.
- [x] Commit the CLI boundary.

### Task 3: Project immutable comparison evidence to versioned JSON

**Files:**
- Modify: `src/rankweave/cli.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_contracts.py`

**Interfaces:**
- Produces `comparison_to_dict(report) -> dict[str, object]`.
- Consumes `compare_trec_runs(...) -> TrecRunComparisonReport`.

- [x] Call `compare_trec_runs` with every parsed option.
- [x] Build the fixed-order v1 dictionary with package version, run IDs,
  configuration, aggregate values, method, p-value, and ordered per-query data.
- [x] Emit compact JSON by default and two-space indentation for `--pretty`,
  always `ensure_ascii=False` and one trailing newline.
- [x] Confirm no stdout is emitted before all validation and JSON construction
  succeeds.
- [x] Reject projection of a non-`TrecRunComparisonReport` object.
- [x] Run successful compact/pretty/Unicode tests.
- [x] Commit JSON reporting.

### Task 4: Add module and console entrypoints

**Files:**
- Create: `src/rankweave/__main__.py`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_module_entrypoint.py`

**Interfaces:**
- `python -m rankweave` and installed `rankweave` console script both execute
  `rankweave.cli:main`.

- [x] Add the trivial module entrypoint.
- [x] Add `[project.scripts]` mapping.
- [x] Require both new modules in wheel contents.
- [x] Smoke-test the installed console command with temporary TREC files and
  validate the JSON output outside the source tree.
- [x] Compare installed console and module-entrypoint output.
- [x] Run module-entrypoint and package tests.
- [x] Commit packaging integration.

### Task 5: Document and release RankWeave 0.10.0

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Create: `docs/cli.md`
- Modify: `pyproject.toml`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`

**Interfaces:**
- Synchronizes all public release metadata at `0.10.0`.

- [x] Document installation, command syntax, JSON schema, exit codes, limits,
  shell usage, and interpretation boundaries.
- [x] Add CLI adapter/no-duplication and stdout/stderr contracts to AGENTS.
- [x] Cut the 0.10.0 CHANGELOG section.
- [x] Bump project version, public version, and expected-version test together.
- [x] Integrate the 0.9.0 candidate-family prerequisite into the stacked branch
  without dropping its public API, tests, documentation, or APA 7 references.
- [ ] Run exact-head Ruff, full tests, 100% line/branch coverage, wheel
  verification, isolated console smoke, security, SAST, and `pip check` after
  the final stacked integration.
- [ ] Merge prerequisite PR #18, establish the new `main` commit as an ancestor
  of this branch, request independent current-head review, and merge only after
  repository policy is satisfied.
- [ ] Create the release tag and GitHub Release only after the merged source and
  release artifacts are exact-head verified.
