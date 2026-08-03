import pytest

from rankweave.trec import (
    TrecQrelEntry,
    TrecRun,
    TrecRunEntry,
    format_trec_qrels,
    parse_trec_qrels,
    parse_trec_run,
)


def test_run_tag_accepts_portable_nist_punctuation_and_twenty_characters():
    run_tag = "NIST-prise.tfidf_123"
    assert len(run_tag) == 20

    run = parse_trec_run(f"1 Q0 doc-a 1 0.9 {run_tag}\n")

    assert run.run_id == run_tag
    assert TrecRun(
        run_tag,
        (TrecRunEntry("1", "Q0", "doc-a", 1, 0.9, run_tag),),
    ) == run


@pytest.mark.parametrize(
    "run_tag",
    [
        "",
        "a" * 21,
        "bad/tag",
        "bad tag",
        "ümlaut",
    ],
)
def test_run_tag_rejects_values_outside_portable_nist_profile(run_tag):
    with pytest.raises(ValueError, match="run tag"):
        TrecRunEntry("1", "Q0", "doc-a", 1, 0.9, run_tag)


@pytest.mark.parametrize("relevance", [1.5, True, "1", 128, -128])
def test_public_qrel_entry_requires_bounded_integer_relevance(relevance):
    with pytest.raises(ValueError, match=r"relevance.*integer.*-127.*127"):
        TrecQrelEntry("1", "0", "doc-a", relevance)


@pytest.mark.parametrize("raw_relevance", ["1.5", "nan", "inf", "128", "-128"])
def test_qrels_parser_requires_bounded_ascii_integer_relevance(raw_relevance):
    with pytest.raises(
        ValueError,
        match=r"line 1 relevance must be an integer within \[-127, 127\]",
    ):
        parse_trec_qrels(f"1 0 doc-a {raw_relevance}\n")


def test_qrels_accept_boundary_relevance_and_format_as_integers():
    qrels = parse_trec_qrels("1 0 low -127\n1 0 high 127\n")

    assert [entry.relevance for entry in qrels.entries] == [-127, 127]
    assert format_trec_qrels(qrels) == "1 0 low -127\n1 0 high 127\n"


def test_trec_parsers_ignore_blank_and_comment_lines():
    qrels = parse_trec_qrels(
        "# qrels comment\n"
        "\n"
        "   # indented qrels comment\n"
        "1 0 doc-a 1\n"
    )
    run = parse_trec_run(
        "# run comment\n"
        "\n"
        "   # indented run comment\n"
        "1 Q0 doc-a 1 0.9 run-1\n"
    )

    assert qrels.relevance_by_query() == {"1": {"doc-a": 1}}
    assert run.rankings_by_query() == {"1": ("doc-a",)}


def test_comment_skipping_preserves_physical_error_line_number():
    with pytest.raises(ValueError, match="line 3 must contain 4 fields"):
        parse_trec_qrels("# comment\n\n1 0 doc-a\n")
