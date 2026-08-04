# TREC Comparison CLI Design

## Goal

Provide a stable, dependency-free command-line entrypoint that compares a
baseline TREC run with a candidate run against shared qrels and emits one
machine-readable JSON audit report.

## Buyer problem

RankWeave can compare TREC artifacts through Python, but benchmark operators,
CI pipelines, evaluation engineers, and procurement reviewers should not need
to write Python glue merely to run one controlled comparison. A console
interface makes the safe, strict API usable from shell scripts, build systems,
containers, and non-Python orchestration while preserving exactly the same
validation and statistical contracts.

## Command

Install the console script and module entrypoint:

```text
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  [--metric ndcg_at_k] \
  [--alternative two-sided] \
  [--randomizations 10000] \
  [--seed 0] \
  [--max-input-bytes 67108864] \
  [--pretty]
```

Equivalent module invocation:

```text
python -m rankweave compare ...
```

The first release has one subcommand, `compare`. Candidate-family CLI support
is intentionally deferred so the pairwise schema and operating behavior can
stabilize independently.

## Output schema

Successful execution writes exactly one UTF-8 JSON document to standard output
and a trailing newline. The top-level object contains:

- `schema_version`: literal `rankweave.trec-comparison.v1`;
- `rankweave_version`;
- `baseline_run_id` and `candidate_run_id`;
- `cutoff`, `metric_name`, and `alternative`;
- `query_count` and `nonzero_difference_count`;
- `baseline_mean`, `candidate_mean`, and `mean_difference`;
- `p_value`, `method`, `randomizations_evaluated`, and `random_seed`;
- `query_differences`, an ordered array with query ID, baseline value,
  candidate value, and difference.

Query order follows the baseline evaluation. JSON uses `ensure_ascii=False` so
Unicode query IDs remain readable. Compact output is the default; `--pretty`
uses two-space indentation. Keys are emitted in a fixed documented order rather
than alphabetically, and floating-point values remain JSON numbers.

The JSON is intentionally a projection of the immutable comparison evidence,
not a serialization format for reconstructing every internal dataclass. Parsed
TREC entries remain available through the Python API.

## Input boundaries

Every input path is read as bytes and then decoded with strict UTF-8. Before and
after reading, each artifact is checked against `--max-input-bytes`, default
64 MiB (`67108864`) per artifact. This avoids unbounded memory consumption and
closes size-of-check versus size-of-use races where a file grows after `stat`.

- `--max-input-bytes`, `--cutoff`, and `--randomizations` are positive decimal
  integers and reject booleans implicitly because CLI text is parsed directly.
- `--seed` is a signed decimal integer.
- `--metric` and `--alternative` use RankWeave's public supported choices.
- The CLI does not accept URLs, shell expansion, implicit benchmark downloads,
  or compressed archives.
- The CLI does not overwrite files; callers redirect stdout or capture it in
  their orchestration system.

## Error and exit contract

- exit `0`: comparison completed and JSON was written;
- exit `2`: usage, file I/O, UTF-8, size, TREC validation, evaluation, or
  statistical-option error.

Expected failures write one line to standard error:

```text
rankweave: error: <specific message>
```

No JSON is written on failure. Parser, TREC, evaluation, and comparison error
messages are preserved beneath this prefix. Unexpected programmer errors are
not caught and converted to success-like output.

A custom `ArgumentParser.error` implementation raises an internal usage error
rather than terminating inside the parser, so `main(argv)` remains directly
testable and returns the documented status.

## Architecture

Create focused files:

- `src/rankweave/cli.py`: parser construction, bounded UTF-8 reads, report
  projection, JSON emission, and exit handling;
- `src/rankweave/__main__.py`: `raise SystemExit(main())` only.

The CLI calls `compare_trec_runs`; it must not duplicate TREC parsing,
evaluation, query alignment, randomization, or validation logic. The CLI module
may import `rankweave.__version__` lazily inside output construction to avoid an
initialization cycle.

`main` accepts an optional argument sequence and otherwise reads `sys.argv`.
It writes through `sys.stdout` and `sys.stderr` so ordinary capture tools and
pytest `capsys` work without injecting custom streams into the public API.

## Packaging

Add:

```toml
[project.scripts]
rankweave = "rankweave.cli:main"
```

The wheel-content gate must include `rankweave/cli.py` and
`rankweave/__main__.py`. The isolated wheel smoke test runs both package-level
comparison and the installed console command.

## Testing

Tests cover:

- hand-checked successful compact JSON output;
- Unicode query IDs and pretty output;
- console parser defaults and explicit metric/alternative/randomization/seed;
- malformed TREC input with the precise lower-level message;
- missing file, directory path, invalid UTF-8, and pre-read/post-read size
  rejection;
- invalid positive integers and unsupported choices;
- no stdout on failure and stable exit `2`;
- `python -m rankweave` behavior;
- output schema version and field order;
- package-root access to `cli_main` only if intentionally exported;
- wheel console-script and module contents;
- 100% production line and branch coverage and complete docstrings.

## Release

This additive buyer-facing surface advances the package to `0.10.0`. Release
metadata, public version, CHANGELOG, README, AGENTS, wheel checks, and version
tests change together only after exact-head verification.

## Non-goals

No candidate-family subcommand, HTML report, file output option, stdin
multiplexing, gzip support, benchmark download, automatic deployment decision,
confidence interval, or multiple-comparison policy is introduced in this
slice.
