import math

import pytest

from rankweave import normalize_search_text


@pytest.mark.parametrize(
    "invalid_max_characters",
    [0, -1, 1.5, True, "10", math.nan, math.inf],
)
def test_normalization_rejects_invalid_character_limit(invalid_max_characters):
    with pytest.raises(ValueError, match="max_characters"):
        normalize_search_text(
            "query",
            max_characters=invalid_max_characters,
        )


@pytest.mark.parametrize("invalid_raw_text", [None, b"query", 123])
def test_normalization_rejects_non_string_text(invalid_raw_text):
    with pytest.raises(TypeError, match="raw_text must be a string"):
        normalize_search_text(invalid_raw_text)
