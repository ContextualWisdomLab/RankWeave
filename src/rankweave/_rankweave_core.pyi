"""Static types for the packaged RankWeave Rust extension."""


def theoretical_min_max_normalize(
    score: float,
    lower: float,
    upper: float,
) -> float: ...


def convex_combination_score(
    semantic_score: float | None,
    lexical_score: float | None,
    semantic_weight_alpha: float,
) -> float: ...


def reciprocal_rank_fusion_score(
    ranks: list[int],
    rank_constant_eta: int,
) -> float: ...


def rank_semantic_units(
    query_vector: list[float],
    candidates: list[tuple[str, str, list[float]]],
) -> tuple[str, str, str, int, list[tuple[str, str, float]]]: ...


def rank_semantic_units_packed(
    query_vector: list[float],
    candidate_ids: list[tuple[str, str]],
    packed_vectors: bytes,
) -> tuple[str, str, str, int, list[tuple[str, str, float]]]: ...
