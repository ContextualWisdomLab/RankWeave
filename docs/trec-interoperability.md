# TREC interoperability

RankWeave can ingest, validate, preserve, format, and evaluate standard TREC
run and relevance-judgment text without adding a runtime dependency.

## Shared line handling

Both parsers preserve physical line numbers for diagnostics and ignore:

- blank lines;
- lines whose first non-whitespace character is `#`.

A malformed record after comments therefore reports its original physical line,
not a compacted content-line number.

## Supported artifacts

### Relevance judgments (qrels)

`parse_trec_qrels` expects one four-field content record per line:

```text
query_id iteration document_id relevance
```

This follows the NIST qrels convention documented as `TOPIC ITERATION DOCUMENT
RELEVANCY`. Query, iteration, and document identifiers must be non-empty tokens
without whitespace or Unicode control/surrogate characters.

Relevance follows the reference `trec_eval` qrels reader contract:

- signed ASCII-decimal integer syntax;
- inclusive range `[-127, 127]`;
- `bool`, floating-point values, Unicode digits, `NaN`, and infinity are
  rejected by public constructors and text parsers.

Negative relevance values are preserved in immutable `TrecQrelEntry` audit
records but omitted from `TrecQrels.relevance_by_query()`. This models their
common use as explicit unjudged markers while retaining the query identifier,
even when every entry for that query is negative.

Canonical qrels formatting emits integer fields, not floating-point spellings.

### Submitted runs

`parse_trec_run` expects one six-field content record per line:

```text
query_id Q0 document_id rank score run_tag
```

The parser requires:

- the literal second field `Q0`;
- a positive ASCII-decimal rank; zero padding such as `0001` is accepted and
  normalized to integer `1`;
- a finite score;
- one document and one submitted rank per query;
- one run tag for the entire artifact;
- a portable run tag of 1–20 ASCII letters, digits, periods, underscores, or
  hyphens.

The run-tag profile follows current NIST submission guidance while excluding
whitespace, path separators, non-ASCII lookalikes, and control characters at
the interchange boundary.

## Ordering contract

TREC evaluation tools reorder submitted results by decreasing score rather
than trusting the submitted rank column. `TrecRun.rankings_by_query()` follows
that rule.

Exact score ties are a deliberate RankWeave compatibility extension: Python's
stable sort preserves source-file order. The `trec_eval` reference
implementation uses a different deterministic tie rule based on document ID,
and some track tooling leaves ties unspecified. Use distinct scores when exact
cross-tool metric parity is required.

## Fail-closed immutable records

The public dataclasses validate their own state, not only parser-created state.
Constructing `TrecQrelEntry`, `TrecQrels`, `TrecRunEntry`, or `TrecRun`
directly therefore cannot bypass token, relevance, score, duplicate, rank, or
run-tag contracts. Container inputs are snapshotted to tuples so later mutation
of a caller-owned list cannot change an audit artifact.

Canonical formatters accept only validated container types and emit one
newline-terminated record per entry. Run scores use 17 significant digits,
sufficient for exact binary `float` round trips; qrels relevance is emitted as
an integer.

## Deliberately stricter behavior

RankWeave intentionally rejects some inputs that `trec_eval` may tolerate:

- exactly four qrels fields and six run fields are required;
- every run entry must use `Q0` and the same run tag;
- duplicate query/document and query/rank pairs are rejected;
- numeric fields must be finite and within their documented domains;
- public in-memory records must satisfy the same contracts as parsed text.

These constraints make artifacts safe to store, audit, round-trip, and pass
between services without depending on permissive parser side effects.

## Direct evaluation

```python
from rankweave import evaluate_trec_run

report = evaluate_trec_run(
    "q1 Q0 document-a 1 1.0 NIST-run_1\n",
    "q1 0 document-a 2\n",
    cutoff=10,
)

assert report.aggregate.mean_ndcg_at_k == 1.0
```

`evaluate_trec_run` sorts each run by score, removes negative qrels from the
evaluation mapping, and delegates to RankWeave's fail-closed query-set
evaluation. A run and qrels file must therefore contain exactly the same query
IDs; intentionally empty runs should be represented before evaluation rather
than silently dropping a judged query.

## Authoritative references

- NIST TREC qrels format:
  <https://trec.nist.gov/data/qrels_eng/>
- NIST run submission format and score-order evaluation guidance:
  <https://ir.nist.gov/covidSubmit/round3.html>
- NIST `trec_eval` reference implementation:
  <https://github.com/usnistgov/trec_eval>

RankWeave's metric definitions and deliberate nDCG gain difference remain
documented in [`docs/research/README.md`](research/README.md).
