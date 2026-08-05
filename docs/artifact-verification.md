# Exact report-artifact verification

RankWeave compares the exact raw bytes supplied by a caller with the SHA-256 and raw byte-count evidence in a pairwise or candidate-family v2 report. The pure core accepts mappings and immutable `bytes`; the CLI owns strict JSON parsing and bounded filesystem reads.

## Decision contract

- exit `0`: every artifact digest and byte count matches;
- exit `1`: the report and evidence are valid, but one or more artifacts differ;
- exit `2`: usage, filesystem, size, UTF-8, JSON, evidence-shape, or family-order failure.

A family report must preserve exactly the same candidate order in its result array, artifact-evidence array, and repeatable command arguments. Output never includes local paths, report payloads, TREC text, or host metadata.

## Trust boundary

A successful result means only that supplied bytes equal unsigned evidence embedded in the supplied report. It does not authenticate the report producer, validate a digital signature, establish trusted execution, verify provenance, emit an attestation, or establish a SLSA level. Those claims require independent roots of trust and signed provenance or verification attestations.
