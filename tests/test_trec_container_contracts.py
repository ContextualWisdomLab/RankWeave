import pytest

from rankweave import TrecQrelEntry, TrecQrels, TrecRun, TrecRunEntry


def test_public_containers_reject_non_iterable_or_wrong_entry_types():
    with pytest.raises(ValueError, match="iterable of entries"):
        TrecQrels(None)
    with pytest.raises(ValueError, match="iterable of entries"):
        TrecRun("run", None)
    with pytest.raises(ValueError, match="TrecQrelEntry"):
        TrecQrels(("not-a-qrel",))
    with pytest.raises(ValueError, match="TrecRunEntry"):
        TrecRun("run", ("not-a-run-entry",))


def test_public_run_container_rejects_duplicate_document():
    with pytest.raises(ValueError, match="duplicate document"):
        TrecRun(
            "run",
            (
                TrecRunEntry("1", "Q0", "same", 1, 2.0, "run"),
                TrecRunEntry("1", "Q0", "same", 2, 1.0, "run"),
            ),
        )


def test_public_qrels_container_rejects_duplicate_judgment():
    with pytest.raises(ValueError, match="duplicate judgment"):
        TrecQrels(
            (
                TrecQrelEntry("1", "0", "same", 1.0),
                TrecQrelEntry("1", "1", "same", 2.0),
            )
        )
