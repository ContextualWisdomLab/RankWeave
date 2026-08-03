import pytest

from rankweave import weighted_convex_combination_score


def test_weighted_convex_combination_fuses_three_channels():
    score = weighted_convex_combination_score(
        {"semantic": 0.8, "lexical": 0.5, "sparse": 0.6},
        {"semantic": 0.5, "lexical": 0.3, "sparse": 0.2},
    )

    assert score == pytest.approx(0.5 * 0.8 + 0.3 * 0.5 + 0.2 * 0.6)


def test_weighted_convex_combination_missing_scores_contribute_zero():
    weights = {"semantic": 0.7, "lexical": 0.2, "sparse": 0.1}

    assert weighted_convex_combination_score(
        {"semantic": 0.8, "lexical": None}, weights
    ) == pytest.approx(0.56)


def test_weighted_convex_combination_rejects_non_convex_weights():
    with pytest.raises(ValueError, match="sum to 1"):
        weighted_convex_combination_score(
            {"semantic": 0.8, "lexical": 0.5},
            {"semantic": 0.7, "lexical": 0.4},
        )


def test_weighted_convex_combination_rejects_negative_weight():
    with pytest.raises(ValueError, match="non-negative"):
        weighted_convex_combination_score(
            {"semantic": 0.8, "lexical": 0.5},
            {"semantic": 1.1, "lexical": -0.1},
        )


def test_weighted_convex_combination_rejects_unknown_score_channel():
    with pytest.raises(ValueError, match="without weights"):
        weighted_convex_combination_score(
            {"semantic": 0.8, "lexical": 0.5, "sparse": 0.6},
            {"semantic": 0.7, "lexical": 0.3},
        )


@pytest.mark.parametrize("invalid_score", [-0.1, 1.1, float("nan")])
def test_weighted_convex_combination_rejects_score_outside_unit_interval(
    invalid_score,
):
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        weighted_convex_combination_score(
            {"semantic": invalid_score, "lexical": 0.5},
            {"semantic": 0.7, "lexical": 0.3},
        )


def test_weighted_convex_combination_tolerates_serialized_weight_rounding():
    weights = {
        "semantic": 0.178733,
        "lexical": 0.017827,
        "sparse": 0.8034399999999999,
    }

    assert weighted_convex_combination_score(
        {"semantic": 1.0, "lexical": 1.0, "sparse": 1.0}, weights
    ) == pytest.approx(1.0)
