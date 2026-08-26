//! Deterministic calculation primitives for RankWeave.

use std::collections::{HashMap, HashSet};
use std::fmt;

use num_bigint::BigUint;
use num_traits::ToPrimitive;
use sha2::{Digest, Sha256};

/// Version of the semantic-unit ranking result envelope.
pub const SEMANTIC_UNIT_RANKING_SCHEMA_VERSION: &str = "rankweave.semantic-unit-ranking.v1";

/// Version of the semantic-unit cosine calculation contract.
pub const SEMANTIC_UNIT_COSINE_ALGORITHM_VERSION: &str = "rankweave.semantic-unit-cosine.v1";

/// One caller-owned semantic unit and its embedding vector.
#[derive(Clone, Debug, PartialEq)]
pub struct SemanticUnitCandidate {
    /// Opaque identifier for the containing item.
    pub item_id: String,
    /// Opaque identifier for the semantic unit within the item.
    pub unit_id: String,
    /// Provider-produced vector; RankWeave does not select its model.
    pub vector: Vec<f64>,
}

/// The highest-scoring semantic unit retained for one item.
#[derive(Clone, Debug, PartialEq)]
pub struct SemanticUnitRank {
    /// Opaque caller-owned item identifier.
    pub item_id: String,
    /// Opaque identifier of the unit that produced `score`.
    pub winning_unit_id: String,
    /// Raw cosine clamped to `[0, 1]`, without remapping or a cutoff.
    pub score: f64,
}

/// Versioned, reproducible semantic-unit ranking evidence.
#[derive(Clone, Debug, PartialEq)]
pub struct SemanticUnitRankingReport {
    /// Stable result-envelope identifier.
    pub schema_version: &'static str,
    /// Stable calculation-contract identifier.
    pub algorithm_version: &'static str,
    /// SHA-256 over the canonical ordered request bytes.
    pub ordered_input_digest: String,
    /// Exact dimension shared by every accepted vector.
    pub vector_dimension: usize,
    /// Results sorted by descending score, then item identifier.
    pub results: Vec<SemanticUnitRank>,
}

/// Explicit fail-closed semantic-unit ranking failures.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SemanticUnitRankingError {
    /// The query vector has no dimensions.
    EmptyQueryVector,
    /// No candidate semantic unit was supplied.
    EmptyCandidates,
    /// A vector contains NaN or infinity.
    NonFiniteVector { vector_label: String },
    /// A candidate dimension differs from the query dimension.
    DimensionMismatch {
        vector_label: String,
        expected: usize,
        actual: usize,
    },
    /// Cosine is undefined for an all-zero vector.
    ZeroNormVector { vector_label: String },
    /// An item/unit identity pair occurs more than once.
    DuplicateCandidate { item_id: String, unit_id: String },
}

impl SemanticUnitRankingError {
    /// Stable machine-readable failure code.
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::EmptyQueryVector => "empty_query_vector",
            Self::EmptyCandidates => "empty_candidates",
            Self::NonFiniteVector { .. } => "non_finite_vector",
            Self::DimensionMismatch { .. } => "dimension_mismatch",
            Self::ZeroNormVector { .. } => "zero_norm_vector",
            Self::DuplicateCandidate { .. } => "duplicate_candidate",
        }
    }
}

impl fmt::Display for SemanticUnitRankingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyQueryVector => formatter.write_str("query vector must not be empty"),
            Self::EmptyCandidates => formatter.write_str("candidates must not be empty"),
            Self::NonFiniteVector { vector_label } => {
                write!(formatter, "{vector_label} must contain only finite values")
            }
            Self::DimensionMismatch {
                vector_label,
                expected,
                actual,
            } => write!(
                formatter,
                "{vector_label} dimension must be {expected}, got {actual}"
            ),
            Self::ZeroNormVector { vector_label } => {
                write!(formatter, "{vector_label} must have a non-zero norm")
            }
            Self::DuplicateCandidate { item_id, unit_id } => write!(
                formatter,
                "candidate ({item_id:?}, {unit_id:?}) must be unique"
            ),
        }
    }
}

impl std::error::Error for SemanticUnitRankingError {}

fn validate_vector(
    vector: &[f64],
    expected_dimension: usize,
    vector_label: String,
) -> Result<(), SemanticUnitRankingError> {
    if vector.len() != expected_dimension {
        return Err(SemanticUnitRankingError::DimensionMismatch {
            vector_label,
            expected: expected_dimension,
            actual: vector.len(),
        });
    }
    if vector.iter().any(|value| !value.is_finite()) {
        return Err(SemanticUnitRankingError::NonFiniteVector { vector_label });
    }
    if vector.iter().all(|value| *value == 0.0) {
        return Err(SemanticUnitRankingError::ZeroNormVector { vector_label });
    }
    Ok(())
}

fn cosine_similarity(left: &[f64], right: &[f64]) -> f64 {
    let left_scale = left.iter().map(|value| value.abs()).fold(0.0, f64::max);
    let right_scale = right.iter().map(|value| value.abs()).fold(0.0, f64::max);
    let (dot, left_squared, right_squared) = left.iter().zip(right).fold(
        (0.0, 0.0, 0.0),
        |(dot, left_squared, right_squared), (left_value, right_value)| {
            let scaled_left = left_value / left_scale;
            let scaled_right = right_value / right_scale;
            (
                dot + scaled_left * scaled_right,
                left_squared + scaled_left * scaled_left,
                right_squared + scaled_right * scaled_right,
            )
        },
    );
    (dot / (left_squared.sqrt() * right_squared.sqrt())).clamp(0.0, 1.0)
}

fn update_length_prefixed(hasher: &mut Sha256, value: &[u8]) {
    hasher.update((value.len() as u64).to_be_bytes());
    hasher.update(value);
}

fn ordered_input_digest(query_vector: &[f64], candidates: &[SemanticUnitCandidate]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(b"rankweave.semantic-unit-ranking.request.v1\0");
    hasher.update((query_vector.len() as u64).to_be_bytes());
    for value in query_vector {
        hasher.update(value.to_bits().to_be_bytes());
    }
    hasher.update((candidates.len() as u64).to_be_bytes());
    for candidate in candidates {
        update_length_prefixed(&mut hasher, candidate.item_id.as_bytes());
        update_length_prefixed(&mut hasher, candidate.unit_id.as_bytes());
        hasher.update((candidate.vector.len() as u64).to_be_bytes());
        for value in &candidate.vector {
            hasher.update(value.to_bits().to_be_bytes());
        }
    }
    format!("sha256:{:x}", hasher.finalize())
}

/// Rank items by their best caller-supplied semantic-unit cosine evidence.
///
/// Candidate order is part of the digest, while result order is descending
/// score then ascending item identifier. Equal-scoring units for one item use
/// ascending unit identifier. No model, weight, threshold, or authorization
/// decision is made here.
pub fn rank_semantic_units(
    query_vector: &[f64],
    candidates: &[SemanticUnitCandidate],
) -> Result<SemanticUnitRankingReport, SemanticUnitRankingError> {
    if query_vector.is_empty() {
        return Err(SemanticUnitRankingError::EmptyQueryVector);
    }
    if candidates.is_empty() {
        return Err(SemanticUnitRankingError::EmptyCandidates);
    }
    validate_vector(query_vector, query_vector.len(), "query vector".to_owned())?;

    let mut identities = HashSet::new();
    let mut best_by_item: HashMap<String, SemanticUnitRank> = HashMap::new();
    for candidate in candidates {
        if !identities.insert((candidate.item_id.as_str(), candidate.unit_id.as_str())) {
            return Err(SemanticUnitRankingError::DuplicateCandidate {
                item_id: candidate.item_id.clone(),
                unit_id: candidate.unit_id.clone(),
            });
        }
        let vector_label = format!(
            "candidate vector for item {:?}, unit {:?}",
            candidate.item_id, candidate.unit_id
        );
        validate_vector(&candidate.vector, query_vector.len(), vector_label)?;
        let score = cosine_similarity(query_vector, &candidate.vector);
        let proposed = SemanticUnitRank {
            item_id: candidate.item_id.clone(),
            winning_unit_id: candidate.unit_id.clone(),
            score,
        };
        best_by_item
            .entry(candidate.item_id.clone())
            .and_modify(|current| {
                if proposed.score > current.score
                    || (proposed.score == current.score
                        && proposed.winning_unit_id < current.winning_unit_id)
                {
                    *current = proposed.clone();
                }
            })
            .or_insert(proposed);
    }

    let mut results: Vec<_> = best_by_item.into_values().collect();
    results.sort_by(|left, right| {
        right
            .score
            .total_cmp(&left.score)
            .then_with(|| left.item_id.cmp(&right.item_id))
    });
    Ok(SemanticUnitRankingReport {
        schema_version: SEMANTIC_UNIT_RANKING_SCHEMA_VERSION,
        algorithm_version: SEMANTIC_UNIT_COSINE_ALGORITHM_VERSION,
        ordered_input_digest: ordered_input_digest(query_vector, candidates),
        vector_dimension: query_vector.len(),
        results,
    })
}

/// Scale a finite score with finite theoretical bounds and clamp it to `[0, 1]`.
#[must_use]
pub fn theoretical_min_max_normalize(score: f64, lower: f64, upper: f64) -> f64 {
    ((score - lower) / (upper - lower)).clamp(0.0, 1.0)
}

/// Combine two normalized scores using the caller-supplied semantic weight.
///
/// Missing candidate evidence is represented by `None` and contributes the
/// documented theoretical minimum, zero. Validation remains at the public
/// Python boundary; this function owns only the deterministic arithmetic.
#[must_use]
pub fn convex_combination_score(
    semantic_score: Option<f64>,
    lexical_score: Option<f64>,
    semantic_weight_alpha: f64,
) -> f64 {
    let semantic_component = semantic_score.unwrap_or(0.0);
    let lexical_component = lexical_score.unwrap_or(0.0);
    semantic_weight_alpha * semantic_component + (1.0 - semantic_weight_alpha) * lexical_component
}

/// Sum Reciprocal Rank Fusion contributions in caller-provided channel order.
#[must_use]
pub fn reciprocal_rank_fusion_score(ranks: &[BigUint], rank_constant_eta: &BigUint) -> f64 {
    ranks.iter().fold(0.0, |score, rank| {
        let denominator = (rank_constant_eta + rank).to_f64().unwrap_or(f64::INFINITY);
        score + 1.0 / denominator
    })
}

#[cfg(test)]
mod tests {
    use super::{
        SemanticUnitCandidate, SemanticUnitRankingError, convex_combination_score,
        rank_semantic_units, reciprocal_rank_fusion_score, theoretical_min_max_normalize,
    };
    use num_bigint::BigUint;

    #[test]
    fn normalization_uses_theoretical_bounds_and_clamps() {
        assert_eq!(theoretical_min_max_normalize(0.5, 0.0, 2.0), 0.25);
        assert_eq!(theoretical_min_max_normalize(3.0, 0.0, 2.0), 1.0);
    }

    #[test]
    fn convex_fusion_preserves_formula_and_missing_evidence_semantics() {
        assert_eq!(
            convex_combination_score(Some(0.8), Some(0.5), 0.7),
            0.7 * 0.8 + (1.0 - 0.7) * 0.5
        );
        assert_eq!(
            convex_combination_score(None, Some(0.5), 0.7),
            (1.0 - 0.7) * 0.5
        );
        assert_eq!(convex_combination_score(Some(0.8), None, 0.7), 0.7 * 0.8);
        assert_eq!(convex_combination_score(None, None, 0.7), 0.0);
    }

    #[test]
    fn rrf_preserves_input_order_for_the_reduction() {
        let ranks = [BigUint::from(1_u8), BigUint::from(3_u8)];
        assert_eq!(
            reciprocal_rank_fusion_score(&ranks, &BigUint::from(60_u8)),
            1.0 / 61.0 + 1.0 / 63.0
        );
    }

    fn candidate(item_id: &str, unit_id: &str, vector: &[f64]) -> SemanticUnitCandidate {
        SemanticUnitCandidate {
            item_id: item_id.to_owned(),
            unit_id: unit_id.to_owned(),
            vector: vector.to_vec(),
        }
    }

    #[test]
    fn semantic_units_rank_by_best_unit_then_item_id() {
        let candidates = vec![
            candidate("item-b", "unit-z", &[1.0, 0.0]),
            candidate("item-a", "unit-z", &[1.0, 0.0]),
            candidate("item-c", "unit-b", &[-1.0, 0.0]),
            candidate("item-c", "unit-a", &[0.0, 1.0]),
            candidate("item-c", "unit-c", &[-1.0, 0.0]),
        ];
        let report = rank_semantic_units(&[1.0, 0.0], &candidates).unwrap();

        assert_eq!(report.schema_version, "rankweave.semantic-unit-ranking.v1");
        assert_eq!(
            report.algorithm_version,
            "rankweave.semantic-unit-cosine.v1"
        );
        assert!(report.ordered_input_digest.starts_with("sha256:"));
        assert_eq!(report.vector_dimension, 2);
        assert_eq!(report.results[0].item_id, "item-a");
        assert_eq!(report.results[1].item_id, "item-b");
        assert_eq!(report.results[2].winning_unit_id, "unit-a");
        assert_eq!(report.results[2].score, 0.0);
    }

    #[test]
    fn semantic_unit_digest_binds_order_and_exact_float_bits() {
        let first = vec![
            candidate("item-a", "unit-a", &[1.0, 0.0]),
            candidate("item-b", "unit-b", &[0.0, 1.0]),
        ];
        let reversed = vec![first[1].clone(), first[0].clone()];
        let first_report = rank_semantic_units(&[1.0, 0.0], &first).unwrap();
        let repeated_report = rank_semantic_units(&[1.0, 0.0], &first).unwrap();
        let reversed_report = rank_semantic_units(&[1.0, 0.0], &reversed).unwrap();

        assert_eq!(
            first_report.ordered_input_digest,
            repeated_report.ordered_input_digest
        );
        assert_ne!(
            first_report.ordered_input_digest,
            reversed_report.ordered_input_digest
        );
    }

    #[test]
    fn semantic_unit_cosine_avoids_finite_vector_overflow() {
        let report = rank_semantic_units(
            &[f64::MAX, f64::MAX],
            &[candidate("item", "unit", &[f64::MAX, f64::MAX])],
        )
        .unwrap();
        assert!(report.results[0].score.is_finite());
        assert!(report.results[0].score > 0.999_999_999_999);
    }

    #[test]
    fn semantic_unit_validation_failures_are_explicit() {
        let cases = [
            (
                rank_semantic_units(&[], &[candidate("item", "unit", &[1.0])]),
                "empty_query_vector",
            ),
            (rank_semantic_units(&[1.0], &[]), "empty_candidates"),
            (
                rank_semantic_units(&[f64::NAN], &[candidate("item", "unit", &[1.0])]),
                "non_finite_vector",
            ),
            (
                rank_semantic_units(&[1.0], &[candidate("item", "unit", &[1.0, 2.0])]),
                "dimension_mismatch",
            ),
            (
                rank_semantic_units(&[0.0], &[candidate("item", "unit", &[1.0])]),
                "zero_norm_vector",
            ),
            (
                rank_semantic_units(&[1.0], &[candidate("item", "unit", &[0.0])]),
                "zero_norm_vector",
            ),
            (
                rank_semantic_units(
                    &[1.0],
                    &[
                        candidate("item", "unit", &[1.0]),
                        candidate("item", "unit", &[1.0]),
                    ],
                ),
                "duplicate_candidate",
            ),
        ];

        for (result, expected_code) in cases {
            let error = result.unwrap_err();
            assert_eq!(error.code(), expected_code);
            assert!(!error.to_string().is_empty());
            assert_eq!(error, error.clone());
            assert!(!format!("{error:?}").is_empty());
        }
        assert_eq!(
            SemanticUnitRankingError::DimensionMismatch {
                vector_label: "candidate".to_owned(),
                expected: 2,
                actual: 1,
            }
            .to_string(),
            "candidate dimension must be 2, got 1"
        );
    }
}
