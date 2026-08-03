"""Query-side text normalization for language-agnostic search.

Character-trigram lexical retrieval is language-agnostic only if the
query and the indexed documents fold *identically*. This module owns
the query-side half of that contract; the store side must mirror it.

1. **Unicode NFC composition (UAX #15).** Vietnamese and Korean text
   arrives in mixed composed/decomposed forms depending on the source
   platform (macOS filenames and some webmail clients emit NFD), so
   both sides must compose before comparison.
2. **Accent folding + lowercasing belong on the store side.** Do them
   where the documents are indexed so the indexed expression and the
   bound query parameter go through the identical path — for example a
   PostgreSQL ``IMMUTABLE`` wrapper
   ``lower(unaccent(normalize(text, NFC)))`` used in a ``pg_trgm``
   GiST expression index. Keep that transform in one place and call it
   from both sides.

Only whitespace shaping and NFC are done here; anything that depends
on the store's runtime (accent dictionaries, collations) stays on the
store side so it cannot silently diverge.
"""

import unicodedata

from rankweave._validation import _require_positive_integer

DEFAULT_MAX_QUERY_CHARACTER_LENGTH = 1000


def normalize_search_text(
    raw_text: str,
    *,
    max_characters: int = DEFAULT_MAX_QUERY_CHARACTER_LENGTH,
) -> str:
    """Compose the query to NFC and collapse insignificant whitespace.

    ``max_characters`` caps pathological queries; set it to match the
    store-side bound. Returns the composed, whitespace-collapsed,
    length-capped query text.

    Raises ``TypeError`` when ``raw_text`` is not a string and ``ValueError``
    when ``max_characters`` is not a positive integer.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")
    validated_max_characters = _require_positive_integer(
        max_characters, "max_characters"
    )
    composed_text = unicodedata.normalize("NFC", raw_text)
    collapsed_text = " ".join(composed_text.split())
    return collapsed_text[:validated_max_characters]
