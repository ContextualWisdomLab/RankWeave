//! Deterministic calculation primitives for RankWeave.

/// Scale a finite score with finite theoretical bounds and clamp it to `[0, 1]`.
#[must_use]
pub fn theoretical_min_max_normalize(score: f64, lower: f64, upper: f64) -> f64 {
    ((score - lower) / (upper - lower)).clamp(0.0, 1.0)
}

/// Sum Reciprocal Rank Fusion contributions in caller-provided channel order.
#[must_use]
pub fn reciprocal_rank_fusion_score(ranks: &[u64], rank_constant_eta: u64) -> f64 {
    ranks.iter().fold(0.0, |score, rank| {
        score + 1.0 / (rank_constant_eta + rank) as f64
    })
}

#[cfg(test)]
mod tests {
    use super::{reciprocal_rank_fusion_score, theoretical_min_max_normalize};

    #[test]
    fn normalization_uses_theoretical_bounds_and_clamps() {
        assert_eq!(theoretical_min_max_normalize(0.5, 0.0, 2.0), 0.25);
        assert_eq!(theoretical_min_max_normalize(3.0, 0.0, 2.0), 1.0);
    }

    #[test]
    fn rrf_preserves_input_order_for_the_reduction() {
        assert_eq!(
            reciprocal_rank_fusion_score(&[1, 3], 60),
            1.0 / 61.0 + 1.0 / 63.0
        );
    }
}
