import pytest

from rankweave import (
    convex_combination_score,
    reciprocal_rank_fusion_score,
    theoretical_min_max_normalize,
    weighted_convex_combination_score,
)


@pytest.mark.parametrize("invalid_score", [True, "0.5"])
def test_convex_fusion_rejects_non_real_score_types(invalid_score):
    with pytest.raises(ValueError, match="semantic_score"):
        convex_combination_score(invalid_score, 0.5, 0.5)


@pytest.mark.parametrize("invalid_weight", [True, "1.0"])
def test_weighted_fusion_rejects_non_real_weight_types(invalid_weight):
    with pytest.raises(ValueError, match="weight for channel 'semantic'"):
        weighted_convex_combination_score(
            {"semantic": 0.5},
            {"semantic": invalid_weight},
        )


@pytest.mark.parametrize("invalid_score", [True, "0.5"])
def test_theoretical_normalization_rejects_non_real_score_types(invalid_score):
    with pytest.raises(ValueError, match="score"):
        theoretical_min_max_normalize(invalid_score, (0.0, 1.0))


@pytest.mark.parametrize(
    "invalid_bounds",
    [(False, 1.0), (0.0, True), ("0.0", 1.0), (0.0, "1.0")],
)
def test_theoretical_normalization_rejects_non_real_bound_types(invalid_bounds):
    with pytest.raises(ValueError, match="bounds must be finite"):
        theoretical_min_max_normalize(0.5, invalid_bounds)


def test_rrf_rejects_wrong_rank_type():
    with pytest.raises(ValueError, match="positive integer"):
        reciprocal_rank_fusion_score({"dense": "1"})
