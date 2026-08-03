import math
from dataclasses import FrozenInstanceError

import pytest

from rankweave.trec import (
    TrecQrelEntry,
    TrecQrels,
    TrecRun,
    TrecRunEntry,
    evaluate_trec_run,
    format_trec_qrels,
    format_trec_run,
    parse_trec_qrels,
    parse_trec_run,
)

QRELS_TEXT = """
1 0 doc-a 3
1 0 doc-b 0
2 1 doc-c 2
2 1 doc-unjudged -1
"""

RUN_TEXT = """
1 Q0 doc-a 2 0.9 rankweave
1 Q0 doc-b 1 0.8 rankweave
2 Q0 doc-d 1 0.5 rankweave
2 Q0 doc-c 2 0.7 rankweave
"""


def test_parse_trec_qrels_preserves_entries_and_builds_judgment_mapping():
    qrels = parse_trec_qrels(QRELS_TEXT)
    assert qrels.entries == (
        TrecQrelEntry("1", "0", "doc-a", 3),
        TrecQrelEntry("1", "0", "doc-b", 0),
        TrecQrelEntry("2", "1", "doc-c", 2),
        TrecQrelEntry("2", "1", "doc-unjudged", -1),
    )
    assert qrels.relevance_by_query() == {
        "1": {"doc-a": 3, "doc-b": 0},
        "2": {"doc-c": 2},
    }


def test_parse_trec_qrels_keeps_negative_only_query_in_mapping():
    assert parse_trec_qrels("query 0 document -1\n").relevance_by_query() == {
        "query": {}
    }


def test_parse_trec_qrels_ignores_blank_lines():
    assert len(parse_trec_qrels("\n1 0 doc-a 1\n\n").entries) == 1


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "at least one qrels entry"),
        ("1 0 doc-a", "line 1 must contain 4 fields"),
        (
            "1 0 doc-a nope",
            r"line 1 relevance must be an integer within \[-127, 127\]",
        ),
        (
            "1 0 doc-a nan",
            r"line 1 relevance must be an integer within \[-127, 127\]",
        ),
        (
            "1 0 doc-a inf",
            r"line 1 relevance must be an integer within \[-127, 127\]",
        ),
    ],
)
def test_parse_trec_qrels_rejects_malformed_input(text, message):
    with pytest.raises(ValueError, match=message):
        parse_trec_qrels(text)


def test_parse_trec_qrels_rejects_duplicate_query_document_judgment():
    with pytest.raises(ValueError, match="duplicate judgment.*line 2"):
        parse_trec_qrels("1 0 doc-a 1\n1 1 doc-a 2\n")


def test_parse_trec_qrels_rejects_non_text_input():
    with pytest.raises(ValueError, match="qrels_text must be text"):
        parse_trec_qrels(None)


def test_parse_trec_run_preserves_entries_and_uses_score_order():
    run = parse_trec_run(RUN_TEXT)
    assert run.run_id == "rankweave"
    assert run.entries == (
        TrecRunEntry("1", "Q0", "doc-a", 2, 0.9, "rankweave"),
        TrecRunEntry("1", "Q0", "doc-b", 1, 0.8, "rankweave"),
        TrecRunEntry("2", "Q0", "doc-d", 1, 0.5, "rankweave"),
        TrecRunEntry("2", "Q0", "doc-c", 2, 0.7, "rankweave"),
    )
    assert run.rankings_by_query() == {
        "1": ("doc-a", "doc-b"),
        "2": ("doc-c", "doc-d"),
    }


def test_trec_run_score_ties_preserve_input_order_deterministically():
    run = parse_trec_run(
        "1 Q0 first 2 0.5 tied\n"
        "1 Q0 second 1 0.5 tied\n"
    )
    assert run.rankings_by_query() == {"1": ("first", "second")}


def test_trec_run_accepts_zero_padded_decimal_rank():
    run = parse_trec_run("1 Q0 doc-a 0001 0.5 run1\n")
    assert run.entries[0].rank == 1


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "at least one run entry"),
        ("1 Q0 doc-a 1 0.9", "line 1 must contain 6 fields"),
        ("1 X doc-a 1 0.9 run", "line 1 second field must be Q0"),
        ("1 Q0 doc-a 0 0.9 run", "line 1 rank must be a positive integer"),
        ("1 Q0 doc-a 1.5 0.9 run", "line 1 rank must be a positive integer"),
        ("1 Q0 doc-a 1 nope run", "line 1 score must be a finite number"),
        ("1 Q0 doc-a 1 nan run", "line 1 score must be a finite number"),
        ("1 Q0 doc-a 1 0.9 bad/tag", "line 1 run tag is invalid"),
        (
            "1 Q0 doc-a 1 0.9 abcdefghijklmnopqrstu",
            "line 1 run tag is invalid",
        ),
    ],
)
def test_parse_trec_run_rejects_malformed_input(text, message):
    with pytest.raises(ValueError, match=message):
        parse_trec_run(text)


def test_parse_trec_run_rejects_mixed_run_tags():
    with pytest.raises(ValueError, match="all run entries must use the same run tag"):
        parse_trec_run(
            "1 Q0 doc-a 1 0.9 first\n"
            "2 Q0 doc-b 1 0.8 second\n"
        )


def test_parse_trec_run_rejects_duplicate_query_document():
    with pytest.raises(ValueError, match="duplicate document.*line 2"):
        parse_trec_run(
            "1 Q0 doc-a 1 0.9 run\n"
            "1 Q0 doc-a 2 0.8 run\n"
        )


def test_parse_trec_run_rejects_duplicate_query_rank():
    with pytest.raises(ValueError, match="duplicate rank.*line 2"):
        parse_trec_run(
            "1 Q0 doc-a 1 0.9 run\n"
            "1 Q0 doc-b 1 0.8 run\n"
        )


def test_parse_trec_run_rejects_non_text_input():
    with pytest.raises(ValueError, match="run_text must be text"):
        parse_trec_run(None)


def test_trec_formatters_emit_canonical_round_trippable_text():
    qrels = parse_trec_qrels(QRELS_TEXT)
    run = parse_trec_run(RUN_TEXT)
    qrels_text = format_trec_qrels(qrels)
    run_text = format_trec_run(run)
    assert qrels_text.endswith("\n")
    assert run_text.endswith("\n")
    assert parse_trec_qrels(qrels_text) == qrels
    assert parse_trec_run(run_text) == run


def test_trec_formatters_reject_wrong_types():
    with pytest.raises(ValueError, match="qrels must be TrecQrels"):
        format_trec_qrels([])
    with pytest.raises(ValueError, match="run must be TrecRun"):
        format_trec_run([])


def test_evaluate_trec_run_uses_score_sorted_run_and_qrels():
    report = evaluate_trec_run(RUN_TEXT, QRELS_TEXT, cutoff=2)
    assert report.aggregate.query_count == 2
    assert report.query_metrics[0].query_id == "1"
    assert report.query_metrics[0].metrics.ndcg_at_k == 1.0
    assert report.query_metrics[1].metrics.reciprocal_rank_at_k == 1.0


def test_evaluate_trec_run_fails_closed_on_query_set_mismatch():
    with pytest.raises(ValueError, match="query sets must match"):
        evaluate_trec_run(
            "1 Q0 doc-a 1 1.0 run\n",
            "2 0 doc-a 1\n",
            cutoff=1,
        )


def test_trec_records_are_immutable():
    qrel_entry = TrecQrelEntry("1", "0", "doc-a", 1)
    qrels = TrecQrels((qrel_entry,))
    run_entry = TrecRunEntry("1", "Q0", "doc-a", 1, 1.0, "run")
    run = TrecRun("run", (run_entry,))
    with pytest.raises(FrozenInstanceError):
        qrel_entry.relevance = 0
    with pytest.raises(FrozenInstanceError):
        qrels.entries = ()
    with pytest.raises(FrozenInstanceError):
        run_entry.score = 0.0
    with pytest.raises(FrozenInstanceError):
        run.run_id = "other"


def test_trec_containers_snapshot_list_inputs_as_tuples():
    qrel_entries = [TrecQrelEntry("1", "0", "d", 1)]
    run_entries = [TrecRunEntry("1", "Q0", "d", 1, 1.0, "run")]
    qrels = TrecQrels(qrel_entries)
    run = TrecRun("run", run_entries)
    qrel_entries.clear()
    run_entries.clear()
    assert len(qrels.entries) == 1
    assert len(run.entries) == 1
    assert isinstance(qrels.entries, tuple)
    assert isinstance(run.entries, tuple)


@pytest.mark.parametrize(
    "entry_factory",
    [
        lambda: TrecQrelEntry("bad query", "0", "doc", 1),
        lambda: TrecQrelEntry("q", "0", "bad\ndoc", 1),
        lambda: TrecQrelEntry("q", "0", "doc", math.inf),
        lambda: TrecRunEntry("q", "Q0", "doc", 0, 1.0, "run"),
        lambda: TrecRunEntry("q", "Q0", "doc", 1, math.nan, "run"),
        lambda: TrecRunEntry("q", "Q1", "doc", 1, 1.0, "run"),
        lambda: TrecRunEntry("q", "Q0", "doc", 1, 1.0, "bad/tag"),
    ],
)
def test_public_entries_reject_unserializable_state(entry_factory):
    with pytest.raises(ValueError):
        entry_factory()


def test_public_containers_reject_empty_or_inconsistent_state():
    with pytest.raises(ValueError, match="at least one"):
        TrecQrels(())
    with pytest.raises(ValueError, match="at least one"):
        TrecRun("run", ())
    with pytest.raises(ValueError, match="run tag"):
        TrecRun("other", (TrecRunEntry("1", "Q0", "d", 1, 1.0, "run"),))
    with pytest.raises(ValueError, match="duplicate"):
        TrecQrels(
            (
                TrecQrelEntry("1", "0", "d", 1),
                TrecQrelEntry("1", "1", "d", 2),
            )
        )
    with pytest.raises(ValueError, match="duplicate rank"):
        TrecRun(
            "run",
            (
                TrecRunEntry("1", "Q0", "a", 1, 2.0, "run"),
                TrecRunEntry("1", "Q0", "b", 1, 1.0, "run"),
            ),
        )


def test_formatting_preserves_finite_run_score_round_trip():
    run = TrecRun(
        "run",
        (TrecRunEntry("1", "Q0", "d", 1, math.pi, "run"),),
    )
    assert parse_trec_run(format_trec_run(run)) == run
