# TREC interoperability

RankWeave can ingest, validate, preserve, format, and evaluate standard TREC
run and relevance-judgment text without adding a runtime dependency.

## Supported artifacts

### Relevance judgments (qrels)

`parse_trec_qrels` expects one non-empty four-field record per physical line:

```text
query_id iteration document_id relevance
```

This follows the NIST qrels convention documented as `TOPIC ITERATION DOCUMENT
RELEVANCY`. Query, iteration, and document identifiers must be non-empty tokens
without whitespace. Relevance must be a finite number.

Finite negative relevance values are preserved in the immutable
`TrecQrelEntry` audit records but omitted from `TrecQrels.relevance_by_query()`.
This models their common use as explicit unjudged markers while retaining the
query identifier, even when every entry for that query is negative.

### Submitted runs

`parse_trec_run` expects one non-empty six-field record per physical line:

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
- a conservative run tag of 1–12 ASCII letters or digits.

The 12-character alphanumeric profile is intentionally stricter than some
track-specific examples. It follows the portable NIST submission guidance and
prevents whitespace, punctuation, path separators, or control characters from
crossing an interchange boundary.

## Ordering contract

TREC evaluation tools reorder submitted results by decreasing score rather
than trusting the submitted rank column. `TrecRun.rankings_by_query()` follows
that rule.

Exact score ties are a deliberate RankWeave compatibility extension: Python's
stable sort preserves source-file order. Reference tools may leave equal-score
tie order arbitrary, so use distinct scores when exact cross-tool metric parity
is required.

## Fail-closed immutable records

The public dataclasses validate their own state, not only parser-created state.
Constructing `TrecQrelEntry`, `TrecQrels`, `TrecRunEntry`, or `TrecRun`
directly therefore cannot bypass token, numeric, duplicate, rank, or run-tag
contracts. Container inputs are snapshotted to tuples so later mutation of a
caller-owned list cannot change an audit artifact.

Canonical formatters accept only these validated container types and emit one
newline-terminated record per entry. Floating-point values use 17 significant
digits, sufficient for exact binary `float` round trips.

## Direct evaluation

```python
from rankweave import evaluate_trec_run

report = evaluate_trec_run(
    "q1 Q0 document-a 1 1.0 rw1\n",
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
