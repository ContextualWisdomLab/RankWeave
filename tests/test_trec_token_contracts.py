import pytest

from rankweave import TrecQrelEntry, TrecRunEntry


@pytest.mark.parametrize(
    "entry_factory",
    [
        lambda: TrecQrelEntry("q\x00", "0", "doc", 1.0),
        lambda: TrecQrelEntry("q", "0", "doc\ud800", 1.0),
        lambda: TrecRunEntry("q\x1f", "Q0", "doc", 1, 1.0, "run"),
    ],
)
def test_public_entries_reject_control_and_surrogate_tokens(entry_factory):
    with pytest.raises(ValueError, match="token"):
        entry_factory()
