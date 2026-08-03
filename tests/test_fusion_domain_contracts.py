import pytest

from rankweave import (
    FusionSettings,
    convex_combination_score,
    reciprocal_rank_fusion_score,
)


@pytest.mark.parametrize(
    ("semantic_score", "lexical_score", "expected_label"),
    [
        (-0.1, 0.5, "semantic_score"),
        (1.1, 0.5, "semantic_score"),
        (0.5, -0.1, "lexical_score"),
        (0.5, 1.1, "lexical_score"),
    ],
)
def test_convex_combination_rejects_scores_outside_unit_interval(
    semantic_score,
    lexical_score,
    expected_label,
):
    with pytest.raises(
        ValueError,
        match=rf"{expected_label} must be within \[0, 1\]",
    ):
        convex_combination_score(semantic_score, lexical_score, 0.7)


@pytest.mark.parametrize("invalid_alpha", [-0.1, 1.1])
def test_convex_combination_rejects_non_convex_alpha(invalid_alpha):
    with pytest.raises(
        ValueError,
        match=r"semantic_weight_alpha must be within \[0, 1\]",
    ):
        convex_combination_score(0.8, 0.5, invalid_alpha)


def test_convex_combination_accepts_unit_interval_boundaries():
    assert convex_combination_score(0.0, 1.0, 0.0) == 1.0
    assert convex_combination_score(1.0, 0.0, 1.0) == 1.0


@pytest.mark.parametrize("invalid_eta", [1.5, True])
def test_fusion_settings_rejects_non_integer_rank_constant(invalid_eta):
    with pytest.raises(
        ValueError,
        match="rank_constant_eta must be a positive integer",
    ):
        FusionSettings(rank_constant_eta=invalid_eta)


@pytest.mark.parametrize("invalid_eta", [1.5, True])
def test_rrf_rejects_non_integer_rank_constant(invalid_eta):
    with pytest.raises(
        ValueError,
        match="rank_constant_eta must be a positive integer",
    ):
        reciprocal_rank_fusion_score({"dense": 1}, invalid_eta)


@pytest.mark.parametrize("invalid_rank", [1.5, True])
def test_rrf_rejects_non_integer_rank(invalid_rank):
    with pytest.raises(
        ValueError,
        match="rank for channel 'dense' must be a positive integer",
    ):
        reciprocal_rank_fusion_score({"dense": invalid_rank})
