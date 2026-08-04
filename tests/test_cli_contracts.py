import sys

import pytest

from rankweave.cli import comparison_to_dict, read_text_bounded


class _RecordingBinaryStream:
    def __init__(self, payload):
        self.payload = payload
        self.requested_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size=-1):
        self.requested_sizes.append(size)
        return self.payload


def test_comparison_projection_rejects_non_report():
    with pytest.raises(ValueError, match="report must be TrecRunComparisonReport"):
        comparison_to_dict(object())


def test_bounded_reader_never_requests_more_than_limit_plus_one(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "bounded.run"
    path.write_bytes(b"x")
    stream = _RecordingBinaryStream(b"12345")
    original_open = type(path).open

    def recording_open(self, *args, **kwargs):
        if self == path:
            return stream
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "open", recording_open)

    with pytest.raises(ValueError, match="exceeds max-input-bytes 4"):
        read_text_bounded(path, 4)

    assert stream.requested_sizes == [5]


def test_bounded_reader_rejects_platform_oversized_limit(tmp_path):
    path = tmp_path / "bounded.run"
    path.write_bytes(b"x")

    with pytest.raises(ValueError, match="too large for this platform"):
        read_text_bounded(path, sys.maxsize)
