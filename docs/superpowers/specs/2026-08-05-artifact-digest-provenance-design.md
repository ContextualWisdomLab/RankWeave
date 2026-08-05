# Artifact-digest provenance design

## Problem

RankWeave's pairwise and candidate-family CLI reports preserve statistical
configuration and complete per-query evidence, but they identify input artifacts
only through TREC run tags. Run tags are descriptive provenance and may repeat;
they do not bind a report to the exact run and qrels bytes that were evaluated.

Enterprise CI, regulated evaluation, and cross-service audit workflows need to
answer a concrete question later: **which exact input bytes produced this
report?** Paths cannot provide that evidence because they are mutable, host
specific, and may disclose local directory structure.

## Decision

Add an opt-in `--include-artifact-digests` flag to both CLI commands. The default
transport remains byte-for-byte compatible with the existing v1 schemas. When
the flag is present, RankWeave emits a v2 schema containing SHA-256 and byte
count evidence for every exact UTF-8 input artifact.

```bash
rankweave compare \
  --baseline-run baseline.run \
  --candidate-run candidate.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests
```

```bash
rankweave compare-family \
  --baseline-run baseline.run \
  --candidate lexical=lexical.run \
  --candidate hybrid=hybrid.run \
  --qrels qrels.txt \
  --cutoff 10 \
  --include-artifact-digests
```

## Compatibility boundary

The default remains:

- `rankweave.trec-comparison.v1`
- `rankweave.trec-family-comparison.v1`

Digest mode uses:

- `rankweave.trec-comparison.v2`
- `rankweave.trec-family-comparison.v2`

A new schema identifier is required because existing consumers may enforce the
exact v1 field set and order. The opt-in flag therefore adds provenance without
silently changing an established transport contract.

## Input evidence model

Each bounded local file is opened once in binary mode. RankWeave:

1. checks the observed file size against the per-artifact ceiling;
2. reads at most `max_input_bytes + 1` bytes;
3. rejects growth beyond the configured ceiling;
4. computes SHA-256 over the exact bytes read;
5. records the exact byte count;
6. decodes the same bytes as strict UTF-8 for TREC parsing.

The digest is over the original bytes, not normalized text. Line endings,
trailing whitespace, comments, and Unicode byte sequences therefore remain part
of artifact identity even when they do not change the evaluated ranking.

The evidence intentionally excludes local paths. Reports may cross machines,
containers, tenants, and organizations without leaking local filesystem
structure.

## Pairwise v2 projection

The v2 report inserts an `artifacts` object after `rankweave_version`:

```json
{
  "schema_version": "rankweave.trec-comparison.v2",
  "rankweave_version": "0.12.0",
  "artifacts": {
    "baseline_run": {
      "sha256": "<64 lowercase hexadecimal characters>",
      "byte_count": 1234
    },
    "candidate_run": {
      "sha256": "<64 lowercase hexadecimal characters>",
      "byte_count": 1180
    },
    "qrels": {
      "sha256": "<64 lowercase hexadecimal characters>",
      "byte_count": 730
    }
  },
  "baseline_run_id": "baseline",
  "candidate_run_id": "candidate"
}
```

All remaining fields preserve the v1 order and meaning.

## Candidate-family v2 projection

The family v2 report inserts:

```json
{
  "artifacts": {
    "baseline_run": {
      "sha256": "...",
      "byte_count": 1234
    },
    "qrels": {
      "sha256": "...",
      "byte_count": 730
    },
    "candidates": [
      {
        "candidate_id": "lexical",
        "sha256": "...",
        "byte_count": 1110
      },
      {
        "candidate_id": "hybrid",
        "sha256": "...",
        "byte_count": 1195
      }
    ]
  }
}
```

Candidate digest entries preserve the explicit command-line order used by the
statistical family and Holm tie-breaking contract.

## Architecture

`cli.py` remains a transport adapter. A frozen internal bounded-artifact record
holds decoded text, SHA-256, and byte count. `read_text_bounded` remains
backward-compatible and returns only decoded text; command execution uses the
richer internal reader.

Projection functions accept optional digest evidence. Absence produces v1
exactly. Presence produces v2. No parser, metric, randomization, or Holm
calculation is duplicated.

The runtime remains standard-library-only and store-agnostic. The feature works
in the standalone package, shell and CI, and when RankWeave is invoked by naruon
or another MSA component.

## Security and interpretation

SHA-256 binds the report to exact input bytes but does **not** authenticate the
producer, sign the report, prove trusted execution, or establish a SLSA level.
Consumers requiring authenticity must protect or sign the report and compare
its digests with independently obtained artifacts.

FIPS 180-4 grounds the SHA-256 algorithm. SLSA v1.2 provenance and verification
guidance motivates binding evidence subjects to artifact digests while keeping
RankWeave's narrower claim explicit.

## Testing

TDD coverage must prove:

- default pairwise and family output remains exact v1;
- digest mode emits the correct v2 identifier and field order;
- SHA-256 is computed from exact raw bytes;
- byte counts use raw bytes rather than Unicode character counts;
- file paths do not appear in JSON;
- candidate digest order matches command-line order;
- equal evaluated content with different raw bytes has different digests;
- console and module entrypoints emit byte-identical v2 JSON;
- bounded reads, strict UTF-8, stderr-only failures, and v1 behavior do not
  regress;
- Python 3.10–3.13, Ruff, production docstrings, statement/branch coverage,
  wheel contents, isolated install, Security Scan, and Semgrep all pass.

## Release

This additive opt-in transport is RankWeave 0.12.0. Synchronize package version,
public version, version regression test, installed-wheel smoke assertions,
README, CLI documentation, `AGENTS.md`, research references, and
`CHANGELOG.md`. Do not create a tag, GitHub Release, or package publication
before protected merge.
