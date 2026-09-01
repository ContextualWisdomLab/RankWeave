# RankWeave

RankWeave is a dependency-free Python toolkit for deterministic retrieval fusion, ranking evaluation, statistical comparison, offline policy selection, and strict TREC interchange.

## Start here

Use RankWeave when a retrieval system needs to combine multiple ranked or scored channels and retain auditable evidence for evaluation and comparison without coupling to a search engine, database, embedding provider, or host application.

The runtime uses only the Python standard library and is designed to work both as a standalone package and as a published dependency consumed by products such as Naruon and LineageWeave.

## Public capabilities

- weighted convex score fusion and reciprocal-rank fusion;
- ranking metrics including precision, recall, reciprocal rank, and graded nDCG;
- paired system comparison and candidate-family correction;
- validation-set policy tuning and explicit fold/time assessment;
- TREC qrels/run parsing, comparison, CLI JSON evidence, and schema contracts;
- exact-byte artifact identity for persisted evaluation evidence.

## Documentation

- [Repository overview and usage](../README.md)
- [Command-line interface](cli.md)
- [Research basis](research.md)
- [Report schemas](report-schemas.md)
- [Release guidance](releasing.md)
- [Product/technical gap baseline](product-technical-gap-baseline.md)

## Release status

Treat the live package index and immutable release evidence as authoritative for what is publicly installable. Repository source, documentation, and active pull requests may describe capabilities that have not yet reached the currently published package version.
