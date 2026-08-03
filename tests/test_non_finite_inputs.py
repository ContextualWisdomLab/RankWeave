import math

import pytest

from rankweave import (
    FusionSettings,
    convex_combination_score,
    fuse_channel_scores,
    reciprocal_rank_fusion_score,
    theoretical_min_max_normalize,
    weighted_convex_combination_score,
)


@pytest.mark.parametrize("non_finite_score", [math.nan, math.inf, -math.inf])
def test_theoretical_normalization_rejects_non_finite_score(non_finite_score):
    with pytest.raises(ValueError, match="score must be finite"):
        theoretical_min_max_normalize(non_finite_score, (0.0, 1.0))


@pytest.mark.parametrize(
    "bounds",
    [
        (math.nan, 1.0),
        (0.0, math.nan),
        (-math.inf, 1.0),
        (0.0, math.inf),
    ],
)
def test_theoretical_normalization_rejects_non_finite_bounds(bounds):
    with pytest.raises(ValueError, match="bounds must be finite"):
        theoretical_min_max_normalize(0.5, bounds)


@pytest.mark.parametrize(
    ("semantic_score", "lexical_score", "semantic_weight_alpha"),
    [
        (math.nan, 0.5, 0.7),
        (0.8, math.inf, 0.7),
        (0.8, 0.5, -math.inf),
    ],
)
def test_convex_combination_rejects_non_finite_inputs(
    semantic_score,
    lexical_score,
    semantic_weight_alpha,
):
    with pytest.raises(ValueError, match="must be finite"):
        convex_combination_score(
            semantic_score,
            lexical_score,
            semantic_weight_alpha,
        )


@pytest.mark.parametrize("non_finite_alpha", [math.nan, math.inf, -math.inf])
def test_fusion_settings_rejects_non_finite_semantic_weight(non_finite_alpha):
    with pytest.raises(ValueError, match="semantic_weight_alpha must be finite"):
        FusionSettings(semantic_weight_alpha=non_finite_alpha)


def test_fusion_settings_rejects_non_finite_rank_constant():
    with pytest.raises(ValueError, match="rank_constant_eta must be finite"):
        FusionSettings(rank_constant_eta=math.nan)


@pytest.mark.parametrize("non_finite_rank", [math.nan, math.inf, -math.inf])
def test_rrf_rejects_non_finite_rank(non_finite_rank):
    with pytest.raises(ValueError, match="rank for channel 'dense' must be finite"):
        reciprocal_rank_fusion_score({"dense": non_finite_rank})


@pytest.mark.parametrize("non_finite_eta", [math.nan, math.inf, -math.inf])
def test_rrf_rejects_non_finite_eta(non_finite_eta):
    with pytest.raises(ValueError, match="rank_constant_eta must be finite"):
        reciprocal_rank_fusion_score({"dense": 1}, non_finite_eta)


@pytest.mark.parametrize("non_finite_weight", [math.nan, math.inf, -math.inf])
def test_weighted_convex_fusion_rejects_non_finite_weight(non_finite_weight):
    with pytest.raises(ValueError, match="weight for channel 'dense' must be finite"):
        weighted_convex_combination_score(
            {"dense": 0.8},
            {"dense": non_finite_weight},
        )


@pytest.mark.parametrize("non_finite_score", [math.nan, math.inf, -math.inf])
def test_weighted_convex_fusion_rejects_non_finite_score(non_finite_score):
    with pytest.raises(ValueError, match="score for channel 'dense' must be finite"):
        weighted_convex_combination_score(
            {"dense": non_finite_score},
            {"dense": 1.0},
        )


@pytest.mark.parametrize(
    ("word_similarity_score", "cosine_distance"),
    [(math.nan, 0.2), (0.7, math.inf)],
)
def test_high_level_fusion_rejects_non_finite_raw_scores(
    word_similarity_score,
    cosine_distance,
):
    with pytest.raises(ValueError, match="score must be finite"):
        fuse_channel_scores(
            word_similarity_score=word_similarity_score,
            cosine_distance=cosine_distance,
            channel_ranks={"lexical": 1, "dense": 1},
            settings=FusionSettings(),
        )
