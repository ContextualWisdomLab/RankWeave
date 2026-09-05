import math

import pytest

from rankweave import (
    COSINE_DISTANCE_THEORETICAL_BOUNDS,
    WORD_SIMILARITY_THEORETICAL_BOUNDS,
    FusionSettings,
    convex_combination_score,
    fuse_channel_scores,
    normalize_search_text,
    reciprocal_rank_fusion_score,
    theoretical_min_max_normalize,
)
from rankweave.score_fusion import (
    CONVEX_COMBINATION_STRATEGY,
    RECIPROCAL_RANK_STRATEGY,
)


class TestNormalizeSearchText:
    def test_composes_decomposed_hangul_to_nfc(self):
        # U+1112 U+1161 U+11AB (decomposed jamo) -> U+D55C
        decomposed_hangul = "\u1112\u1161\u11ab"
        assert normalize_search_text(decomposed_hangul) == "\ud55c"

    def test_composes_decomposed_vietnamese_diacritics(self):
        # "a" + combining circumflex + combining grave -> U+1EA7
        decomposed_vietnamese = "Tra\u0302\u0300n"
        assert normalize_search_text(decomposed_vietnamese) == "Tr\u1ea7n"

    def test_collapses_whitespace_and_strips(self):
        assert normalize_search_text("  hello \t world \n") == "hello world"

    def test_caps_pathological_query_length(self):
        assert len(normalize_search_text("가" * 5000)) == 1000

    def test_keeps_cjk_text_intact_without_tokenization(self):
        korean_query = "다음주 회의 일정"
        assert normalize_search_text(korean_query) == korean_query

    def test_max_characters_override(self):
        assert len(normalize_search_text("a" * 50, max_characters=10)) == 10

    def test_rejects_non_positive_max_characters(self):
        with pytest.raises(ValueError):
            normalize_search_text("hello", max_characters=0)


class TestTheoreticalMinMaxNormalize:
    def test_word_similarity_bounds_map_to_unit_interval(self):
        assert theoretical_min_max_normalize(
            0.0, WORD_SIMILARITY_THEORETICAL_BOUNDS
        ) == 0.0
        assert theoretical_min_max_normalize(
            1.0, WORD_SIMILARITY_THEORETICAL_BOUNDS
        ) == 1.0
        assert theoretical_min_max_normalize(
            0.25, WORD_SIMILARITY_THEORETICAL_BOUNDS
        ) == pytest.approx(0.25)

    def test_cosine_distance_bounds_map_to_unit_interval(self):
        assert theoretical_min_max_normalize(
            0.0, COSINE_DISTANCE_THEORETICAL_BOUNDS
        ) == 0.0
        assert theoretical_min_max_normalize(
            2.0, COSINE_DISTANCE_THEORETICAL_BOUNDS
        ) == 1.0
        assert theoretical_min_max_normalize(
            0.5, COSINE_DISTANCE_THEORETICAL_BOUNDS
        ) == pytest.approx(0.25)

    def test_clamps_floating_point_drift(self):
        assert theoretical_min_max_normalize(
            1.0000001, WORD_SIMILARITY_THEORETICAL_BOUNDS
        ) == 1.0
        assert theoretical_min_max_normalize(
            -0.0000001, WORD_SIMILARITY_THEORETICAL_BOUNDS
        ) == 0.0

    def test_rejects_inverted_bounds(self):
        with pytest.raises(ValueError):
            theoretical_min_max_normalize(0.5, (1.0, 0.0))


class TestConvexCombinationScore:
    def test_hand_computed_fusion(self):
        # alpha * semantic + (1 - alpha) * lexical
        fused_score = convex_combination_score(0.8, 0.5, 0.7)
        assert fused_score == pytest.approx(0.7 * 0.8 + 0.3 * 0.5)

    def test_missing_channel_contributes_theoretical_minimum(self):
        assert convex_combination_score(None, 0.5, 0.7) == pytest.approx(0.15)
        assert convex_combination_score(0.8, None, 0.7) == pytest.approx(0.56)
        assert convex_combination_score(None, None, 0.7) == 0.0

    def test_alpha_extremes_select_single_channel(self):
        assert convex_combination_score(0.9, 0.4, 1.0) == pytest.approx(0.9)
        assert convex_combination_score(0.9, 0.4, 0.0) == pytest.approx(0.4)

    def test_monotone_in_each_channel(self):
        base_score = convex_combination_score(0.5, 0.5, 0.7)
        assert convex_combination_score(0.6, 0.5, 0.7) > base_score
        assert convex_combination_score(0.5, 0.6, 0.7) > base_score

    def test_bounded_in_unit_interval(self):
        assert 0.0 <= convex_combination_score(1.0, 1.0, 0.7) <= 1.0
        assert 0.0 <= convex_combination_score(0.0, 0.0, 0.7) <= 1.0


class TestReciprocalRankFusionScore:
    def test_hand_computed_rrf(self):
        fused_score = reciprocal_rank_fusion_score(
            {"lexical_email": 1, "dense_email": 3}, rank_constant_eta=60
        )
        assert fused_score == pytest.approx(1.0 / 61.0 + 1.0 / 63.0)

    def test_lower_rank_scores_higher(self):
        better_ranked = reciprocal_rank_fusion_score({"channel": 1})
        worse_ranked = reciprocal_rank_fusion_score({"channel": 10})
        assert better_ranked > worse_ranked

    def test_more_channels_score_higher(self):
        single_channel = reciprocal_rank_fusion_score({"a": 5})
        two_channels = reciprocal_rank_fusion_score({"a": 5, "b": 5})
        assert two_channels > single_channel

    def test_rejects_invalid_rank_and_eta(self):
        with pytest.raises(ValueError):
            reciprocal_rank_fusion_score({"a": 0})
        with pytest.raises(ValueError):
            reciprocal_rank_fusion_score({"a": 1}, rank_constant_eta=0)

    def test_preserves_unbounded_python_integer_contract(self):
        rank = 2**64
        assert reciprocal_rank_fusion_score({"channel": rank}) == pytest.approx(
            1.0 / (60 + rank)
        )


class TestFusionSettings:
    def test_defaults_follow_research_grounding(self):
        settings = FusionSettings()
        assert settings.strategy_name == CONVEX_COMBINATION_STRATEGY
        assert settings.semantic_weight_alpha == 0.7
        assert settings.rank_constant_eta == 60

    def test_rejects_unknown_strategy(self):
        with pytest.raises(ValueError):
            FusionSettings(strategy_name="borda_count")

    def test_rejects_out_of_range_alpha(self):
        with pytest.raises(ValueError):
            FusionSettings(semantic_weight_alpha=1.5)


class TestFuseChannelScores:
    def test_convex_strategy_normalizes_and_inverts_distance(self):
        settings = FusionSettings()
        fused_score = fuse_channel_scores(
            word_similarity_score=0.5,
            cosine_distance=0.4,
            channel_ranks={"lexical_email": 1, "dense_email": 1},
            settings=settings,
        )
        expected_semantic = 1.0 - 0.4 / 2.0  # 0.8
        assert fused_score == pytest.approx(0.7 * expected_semantic + 0.3 * 0.5)

    def test_identical_vectors_and_exact_word_match_score_one(self):
        settings = FusionSettings()
        fused_score = fuse_channel_scores(
            word_similarity_score=1.0,
            cosine_distance=0.0,
            channel_ranks={"lexical_email": 1, "dense_email": 1},
            settings=settings,
        )
        assert fused_score == pytest.approx(1.0)

    def test_rrf_strategy_uses_ranks_only(self):
        settings = FusionSettings(strategy_name=RECIPROCAL_RANK_STRATEGY)
        fused_score = fuse_channel_scores(
            word_similarity_score=0.99,
            cosine_distance=0.01,
            channel_ranks={"lexical_email": 2, "dense_email": 4},
            settings=settings,
        )
        assert fused_score == pytest.approx(1.0 / 62.0 + 1.0 / 64.0)

    def test_rrf_strategy_with_no_ranks_scores_zero(self):
        settings = FusionSettings(strategy_name=RECIPROCAL_RANK_STRATEGY)
        assert (
            fuse_channel_scores(
                word_similarity_score=None,
                cosine_distance=None,
                channel_ranks={},
                settings=settings,
            )
            == 0.0
        )

    def test_lexical_only_candidate_is_finite_and_positive(self):
        settings = FusionSettings()
        fused_score = fuse_channel_scores(
            word_similarity_score=0.6,
            cosine_distance=None,
            channel_ranks={"lexical_email": 1},
            settings=settings,
        )
        assert math.isfinite(fused_score)
        assert fused_score == pytest.approx(0.3 * 0.6)
