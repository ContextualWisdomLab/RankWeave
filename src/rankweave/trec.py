"""Strict adapters for standard TREC run and relevance-judgment text."""

import math
import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from rankweave._validation import _require_finite, _require_positive_integer
from rankweave.evaluation import RankingEvaluationReport, evaluate_rankings

_RUN_TAG_PATTERN = re.compile(r"[A-Za-z0-9]{1,12}")


def _require_token(value: str, label: str) -> str:
    """Require a non-empty text token without whitespace or controls."""
    if (
        not isinstance(value, str)
        or not value
        or any(
            character.isspace()
            or unicodedata.category(character) in {"Cc", "Cs"}
            for character in value
        )
    ):
        raise ValueError(
            f"{label} must be a non-empty token without whitespace or controls"
        )
    return value


def _require_run_tag(value: str, label: str) -> str:
    """Require a conservative NIST-compatible alphanumeric run tag."""
    if not isinstance(value, str) or _RUN_TAG_PATTERN.fullmatch(value) is None:
        raise ValueError(
            f"{label} must contain 1 to 12 ASCII letters or digits"
        )
    return value


def _snapshot_entries(entries: Iterable[object], label: str) -> tuple[object, ...]:
    """Snapshot an iterable as a non-empty tuple with a stable error contract."""
    try:
        snapshot = tuple(entries)
    except TypeError as exc:
        raise ValueError(f"{label} must be an iterable of entries") from exc
    if not snapshot:
        raise ValueError(f"{label} must contain at least one entry")
    return snapshot


@dataclass(frozen=True)
class TrecQrelEntry:
    """One four-column TREC relevance judgment."""

    query_id: str
    iteration: str
    document_id: str
    relevance: float

    def __post_init__(self) -> None:
        """Validate and normalize one manually constructed qrels entry."""
        _require_token(self.query_id, "query_id")
        _require_token(self.iteration, "iteration")
        _require_token(self.document_id, "document_id")
        _require_finite(self.relevance, "relevance")
        object.__setattr__(self, "relevance", float(self.relevance))


@dataclass(frozen=True)
class TrecQrels:
    """An immutable parsed TREC relevance-judgment file."""

    entries: tuple[TrecQrelEntry, ...]

    def __post_init__(self) -> None:
        """Snapshot entries and reject duplicate query-document judgments."""
        entries = _snapshot_entries(self.entries, "qrels")
        judged_documents: set[tuple[str, str]] = set()
        for entry in entries:
            if not isinstance(entry, TrecQrelEntry):
                raise ValueError("qrels entries must be TrecQrelEntry values")
            judgment_key = (entry.query_id, entry.document_id)
            if judgment_key in judged_documents:
                raise ValueError(
                    "qrels contains duplicate judgment for query "
                    f"{entry.query_id!r} and document {entry.document_id!r}"
                )
            judged_documents.add(judgment_key)
        object.__setattr__(self, "entries", entries)

    def relevance_by_query(self) -> dict[str, dict[str, float]]:
        """Return evaluation judgments, omitting negative unjudged grades.

        Query identifiers remain present even when every entry for the query
        has a negative grade. This preserves complete-query-set validation in
        :func:`rankweave.evaluate_rankings`.
        """
        relevance_by_query: dict[str, dict[str, float]] = {}
        for entry in self.entries:
            query_relevance = relevance_by_query.setdefault(entry.query_id, {})
            if entry.relevance >= 0.0:
                query_relevance[entry.document_id] = entry.relevance
        return relevance_by_query


@dataclass(frozen=True)
class TrecRunEntry:
    """One six-column TREC run entry."""

    query_id: str
    iteration: str
    document_id: str
    rank: int
    score: float
    run_id: str

    def __post_init__(self) -> None:
        """Validate and normalize one manually constructed run entry."""
        _require_token(self.query_id, "query_id")
        if self.iteration != "Q0":
            raise ValueError("iteration must be Q0")
        _require_token(self.document_id, "document_id")
        validated_rank = _require_positive_integer(self.rank, "rank")
        _require_finite(self.score, "score")
        _require_run_tag(self.run_id, "run tag")
        object.__setattr__(self, "rank", validated_rank)
        object.__setattr__(self, "score", float(self.score))


@dataclass(frozen=True)
class TrecRun:
    """An immutable parsed single-tag TREC run file."""

    run_id: str
    entries: tuple[TrecRunEntry, ...]

    def __post_init__(self) -> None:
        """Snapshot entries and reject inconsistent or duplicate run state."""
        _require_run_tag(self.run_id, "run tag")
        entries = _snapshot_entries(self.entries, "run")
        documents_by_query: dict[str, set[str]] = {}
        ranks_by_query: dict[str, set[int]] = {}
        for entry in entries:
            if not isinstance(entry, TrecRunEntry):
                raise ValueError("run entries must be TrecRunEntry values")
            if entry.run_id != self.run_id:
                raise ValueError(
                    "run tag must match every entry; "
                    f"container={self.run_id!r}, entry={entry.run_id!r}"
                )
            query_documents = documents_by_query.setdefault(entry.query_id, set())
            if entry.document_id in query_documents:
                raise ValueError(
                    f"run contains duplicate document {entry.document_id!r} "
                    f"for query {entry.query_id!r}"
                )
            query_documents.add(entry.document_id)
            query_ranks = ranks_by_query.setdefault(entry.query_id, set())
            if entry.rank in query_ranks:
                raise ValueError(
                    f"run contains duplicate rank {entry.rank} for query "
                    f"{entry.query_id!r}"
                )
            query_ranks.add(entry.rank)
        object.__setattr__(self, "entries", entries)

    def rankings_by_query(self) -> dict[str, tuple[str, ...]]:
        """Return document IDs sorted by decreasing score per query.

        TREC scoring tools ignore the submitted rank column and sort by score.
        Python's stable sort preserves input order for exact score ties, giving
        RankWeave deterministic behavior where ``trec_eval`` leaves tie order
        arbitrary. Use distinct scores when exact cross-tool parity matters.
        """
        entries_by_query: dict[str, list[TrecRunEntry]] = {}
        for entry in self.entries:
            entries_by_query.setdefault(entry.query_id, []).append(entry)
        return {
            query_id: tuple(
                entry.document_id
                for entry in sorted(query_entries, key=lambda item: -item.score)
            )
            for query_id, query_entries in entries_by_query.items()
        }


def _iter_nonempty_lines(text: str, label: str) -> Iterator[tuple[int, str]]:
    """Yield physical line numbers and stripped non-empty lines."""
    if not isinstance(text, str):
        raise ValueError(f"{label} must be text")
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped_line = raw_line.strip()
        if stripped_line:
            yield line_number, stripped_line


def _parse_finite_float(raw_value: str, label: str) -> float:
    """Parse one finite floating-point field with a stable error contract."""
    try:
        parsed_value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(parsed_value):
        raise ValueError(f"{label} must be a finite number")
    return parsed_value


def _parse_positive_rank(raw_rank: str, line_number: int) -> int:
    """Parse a positive ASCII-decimal TREC rank field."""
    if not raw_rank.isascii() or not raw_rank.isdecimal():
        raise ValueError(
            f"line {line_number} rank must be a positive integer"
        )
    parsed_rank = int(raw_rank)
    if parsed_rank < 1:
        raise ValueError(
            f"line {line_number} rank must be a positive integer"
        )
    return parsed_rank


def parse_trec_qrels(qrels_text: str) -> TrecQrels:
    """Parse strict four-column TREC qrels text with line-aware errors.

    The expected columns are ``query iteration document relevance``. Finite
    negative grades are preserved in the audit entries and omitted when
    converting to RankWeave evaluation judgments, matching their common use
    as an explicit unjudged marker.
    """
    entries = []
    judged_documents: set[tuple[str, str]] = set()
    for line_number, line in _iter_nonempty_lines(qrels_text, "qrels_text"):
        fields = line.split()
        if len(fields) != 4:
            raise ValueError(f"line {line_number} must contain 4 fields")
        query_id, iteration, document_id, raw_relevance = fields
        relevance = _parse_finite_float(
            raw_relevance, f"line {line_number} relevance"
        )
        judgment_key = (query_id, document_id)
        if judgment_key in judged_documents:
            raise ValueError(
                f"duplicate judgment for query {query_id!r} and document "
                f"{document_id!r} at line {line_number}"
            )
        judged_documents.add(judgment_key)
        entries.append(
            TrecQrelEntry(
                query_id=query_id,
                iteration=iteration,
                document_id=document_id,
                relevance=relevance,
            )
        )
    if not entries:
        raise ValueError("qrels text must contain at least one qrels entry")
    return TrecQrels(entries=tuple(entries))


def parse_trec_run(run_text: str) -> TrecRun:
    """Parse a strict six-column, single-tag TREC run file.

    The expected columns are ``query Q0 document rank score run-tag``. The
    parser validates the literal ``Q0`` field, positive unique ranks, finite
    scores, one document per query, and one conservative NIST run tag.
    """
    entries = []
    run_id: str | None = None
    documents_by_query: dict[str, set[str]] = {}
    ranks_by_query: dict[str, set[int]] = {}
    for line_number, line in _iter_nonempty_lines(run_text, "run_text"):
        fields = line.split()
        if len(fields) != 6:
            raise ValueError(f"line {line_number} must contain 6 fields")
        query_id, iteration, document_id, raw_rank, raw_score, entry_run_id = fields
        if iteration != "Q0":
            raise ValueError(f"line {line_number} second field must be Q0")
        rank = _parse_positive_rank(raw_rank, line_number)
        score = _parse_finite_float(raw_score, f"line {line_number} score")
        try:
            _require_run_tag(entry_run_id, f"line {line_number} run tag")
        except ValueError as exc:
            raise ValueError(f"line {line_number} run tag is invalid") from exc
        if run_id is None:
            run_id = entry_run_id
        elif entry_run_id != run_id:
            raise ValueError("all run entries must use the same run tag")

        query_documents = documents_by_query.setdefault(query_id, set())
        if document_id in query_documents:
            raise ValueError(
                f"duplicate document {document_id!r} for query {query_id!r} "
                f"at line {line_number}"
            )
        query_documents.add(document_id)

        query_ranks = ranks_by_query.setdefault(query_id, set())
        if rank in query_ranks:
            raise ValueError(
                f"duplicate rank {rank} for query {query_id!r} at line "
                f"{line_number}"
            )
        query_ranks.add(rank)
        entries.append(
            TrecRunEntry(
                query_id=query_id,
                iteration=iteration,
                document_id=document_id,
                rank=rank,
                score=score,
                run_id=entry_run_id,
            )
        )
    if not entries or run_id is None:
        raise ValueError("run text must contain at least one run entry")
    return TrecRun(run_id=run_id, entries=tuple(entries))


def _format_float(value: float) -> str:
    """Format a float with enough precision for exact binary round trips."""
    return format(value, ".17g")


def format_trec_qrels(qrels: TrecQrels) -> str:
    """Serialize validated qrels to canonical whitespace-delimited text."""
    if not isinstance(qrels, TrecQrels):
        raise ValueError("qrels must be TrecQrels")
    return "".join(
        f"{entry.query_id} {entry.iteration} {entry.document_id} "
        f"{_format_float(entry.relevance)}\n"
        for entry in qrels.entries
    )


def format_trec_run(run: TrecRun) -> str:
    """Serialize a validated run to canonical whitespace-delimited text."""
    if not isinstance(run, TrecRun):
        raise ValueError("run must be TrecRun")
    return "".join(
        f"{entry.query_id} {entry.iteration} {entry.document_id} "
        f"{entry.rank} {_format_float(entry.score)} {entry.run_id}\n"
        for entry in run.entries
    )


def evaluate_trec_run(
    run_text: str,
    qrels_text: str,
    *,
    cutoff: int,
) -> RankingEvaluationReport[str]:
    """Parse and evaluate one TREC run against one qrels file."""
    run = parse_trec_run(run_text)
    qrels = parse_trec_qrels(qrels_text)
    return evaluate_rankings(
        run.rankings_by_query(),
        qrels.relevance_by_query(),
        cutoff=cutoff,
    )
