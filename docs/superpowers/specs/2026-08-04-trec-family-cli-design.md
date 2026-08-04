# TREC candidate-family CLI design

## Problem

RankWeave already compares one baseline TREC run with a named family of candidate
runs through `compare_trec_run_family`, including deterministic Holm adjustment.
Shell, CI, container, and non-Python users can only access the pairwise
`rankweave compare` command. They must write Python glue to evaluate a complete
candidate family, which breaks the otherwise closed benchmark workflow and
encourages ad-hoc multiple-comparison handling.

## Decision

Add a `compare-family` subcommand that delegates every ranking, metric,
randomization, and Holm decision to `compare_trec_run_family`.

```bash
rankweave compare-family \
  --baseline-run baseline.run \
  --candidate model-a=artifacts/model-a.run \
  --candidate model-b=artifacts/model-b.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --alternative candidate-greater \
  --familywise-alpha 0.05
```

`--candidate` is repeatable and preserves command-line order. The first `=`
separates a non-empty candidate identifier from its local file path; later `=`
characters remain part of the path. Candidate identifiers must be unique,
printable Unicode strings without leading or trailing whitespace. At least one
candidate is required.

A repeatable option is preferred to a directory scan because it makes the
statistical family explicit and preserves deterministic tie order. It is
preferred to a JSON manifest for this bounded slice because it adds no second
configuration schema and remains natural in shell matrices.

## Input and resource contract

The existing strict UTF-8 bounded reader is reused for the baseline, qrels, and
every candidate. `--max-input-bytes` remains a per-artifact ceiling. The command
accepts local files only and performs no URL fetch, decompression, globbing, or
benchmark download.

`--familywise-alpha` accepts one finite decimal number in `(0, 1]`. Other
statistical options reuse the pairwise CLI defaults and validators. Duplicate
candidate identifiers, malformed `ID=PATH` values, invalid alpha, file errors,
TREC validation failures, incomplete query sets, and statistical validation
errors use the existing stderr-only, exit-2 failure contract.

## Output contract

Success emits one JSON document with schema identifier:

```text
rankweave.trec-family-comparison.v1
```

Top-level fields, in order:

1. `schema_version`
2. `rankweave_version`
3. `baseline_run_id`
4. `cutoff`
5. `metric_name`
6. `alternative`
7. `familywise_alpha`
8. `candidate_count`
9. `candidates`

Each candidate entry contains:

1. `candidate_id`
2. `candidate_run_id`
3. `query_count`
4. `nonzero_difference_count`
5. `baseline_mean`
6. `candidate_mean`
7. `mean_difference`
8. `raw_p_value`
9. `holm_adjusted_p_value`
10. `rejected_at_familywise_alpha`
11. `method`
12. `randomizations_evaluated`
13. `random_seed`
14. `query_differences`

Candidate and query order remain the immutable API order. Unicode identifiers
are emitted without ASCII escaping. Compact JSON is the default and `--pretty`
changes whitespace only.

## Architecture

`cli.py` remains a transport adapter:

- parser construction and option conversion;
- bounded local-file reads;
- ordered candidate specification parsing;
- delegation to `compare_trec_run_family`;
- projection of immutable reports to a versioned JSON schema;
- stable stdout, stderr, and exit status behavior.

No parser, metric, randomization, or Holm formula is duplicated in the CLI.
The runtime remains standard-library-only and store-agnostic, so the feature
works both in the standalone package and when RankWeave is consumed by naruon or
another MSA component.

## Testing

Tests use real temporary run and qrels files and verify:

- command-line order survives into Holm tie handling and JSON output;
- compact and pretty JSON contracts;
- Unicode candidate identifiers;
- projection parity with the immutable family report;
- parser defaults and positive/finite option validation;
- duplicate and malformed candidate specifications;
- precise candidate-specific TREC errors;
- per-artifact bounded-read behavior;
- stderr-only exit-2 failures;
- installed console and module command smoke coverage.

The existing Python 3.10–3.13, Ruff, 100% statement/branch coverage, production
docstring, wheel-content, isolated-install, Security Scan, and Semgrep gates
remain mandatory.

## Release

This additive CLI surface is RankWeave `0.11.0`. Update package metadata,
`rankweave.__version__`, the version regression test, `CHANGELOG.md`, README,
`docs/cli.md`, `AGENTS.md`, and installed-wheel smoke tests together. No tag,
GitHub Release, or package publication occurs before protected merge.

## Evidence

The command exposes the already documented algorithmic contracts rather than
introducing new defaults. Family-wise adjustment remains grounded in Holm
(1979), and TREC interchange remains grounded in the NIST and `trec_eval`
references recorded in `docs/research/README.md` using APA 7th edition format.
