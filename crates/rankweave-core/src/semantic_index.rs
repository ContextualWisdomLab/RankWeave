//! Persistent exact semantic-unit index with deterministic parallel scoring.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::sync::{Arc, RwLock};

use rayon::prelude::*;
use sha2::{Digest, Sha256};

use crate::{SEMANTIC_UNIT_COSINE_ALGORITHM_VERSION, SemanticUnitRank};

/// Version of the immutable exact-index snapshot contract.
pub const SEMANTIC_INDEX_SNAPSHOT_SCHEMA_VERSION: &str =
    "rankweave.semantic-unit-index-snapshot.v1";

/// Deterministic portable CPU execution profile.
pub const SEMANTIC_INDEX_CPU_EXECUTION_PROFILE: &str = "rankweave.semantic-unit-index.cpu-rayon.v1";

/// Immutable evidence describing one validated exact index snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticIndexSnapshotEvidence {
    /// Versioned snapshot-envelope identifier.
    pub schema_version: &'static str,
    /// Caller-owned immutable snapshot version.
    pub snapshot_version: String,
    /// SHA-256 binding the opaque model identity.
    pub model_digest: String,
    /// SHA-256 binding the vector dimension.
    pub dimension_digest: String,
    /// SHA-256 binding candidate identities and exact binary64 values.
    pub vectors_digest: String,
    /// SHA-256 binding all preceding snapshot evidence.
    pub snapshot_digest: String,
    /// Exact vector dimension.
    pub vector_dimension: usize,
    /// Number of indexed semantic units.
    pub candidate_count: usize,
}

/// Versioned exact-ranking result from one immutable index snapshot.
#[derive(Clone, Debug, PartialEq)]
pub struct SemanticIndexRankingReport {
    /// Snapshot evidence used without mutation for this query.
    pub snapshot: SemanticIndexSnapshotEvidence,
    /// Existing exact cosine algorithm version.
    pub algorithm_version: &'static str,
    /// Portable deterministic CPU profile.
    pub execution_profile: &'static str,
    /// Number of Rayon workers visible to the owner runtime.
    pub worker_count: usize,
    /// SHA-256 over the snapshot, query, model, and ordered authorization set.
    pub ordered_input_digest: String,
    /// SHA-256 over the exact ordered result rows.
    pub output_digest: String,
    /// Exact item ranking after per-item maximum pooling.
    pub results: Vec<SemanticUnitRank>,
}

/// Explicit fail-closed snapshot and authorization failures.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SemanticIndexError {
    /// Snapshot version is absent.
    EmptySnapshotVersion,
    /// Model identity is absent.
    EmptyModelIdentity,
    /// Vector dimension is zero.
    EmptyVectorDimension,
    /// Snapshot contains no candidates.
    EmptyCandidates,
    /// Packed vector bytes do not match candidate count and dimension.
    PackedVectorByteLength { expected: usize, actual: usize },
    /// A vector contains NaN or infinity.
    NonFiniteVector { vector_label: String },
    /// A vector has zero norm.
    ZeroNormVector { vector_label: String },
    /// A candidate identity occurs more than once.
    DuplicateCandidate { item_id: String, unit_id: String },
    /// Query model does not match the snapshot model.
    ModelMismatch,
    /// A batch contains no query vectors.
    EmptyQueryBatch,
    /// Query vector dimension does not match the snapshot.
    DimensionMismatch { expected: usize, actual: usize },
    /// Query contains no authorized candidate identities.
    EmptyAuthorization,
    /// An authorized identity occurs more than once.
    DuplicateAuthorization { item_id: String, unit_id: String },
    /// An authorized candidate does not exist in the immutable snapshot.
    UnknownAuthorizedCandidate { item_id: String, unit_id: String },
    /// Packed authorization identities are truncated or have trailing bytes.
    MalformedPackedAuthorization,
    /// A packed authorization identity is not valid UTF-8.
    NonUtf8PackedAuthorization,
    /// The immutable snapshot lock was poisoned.
    SnapshotLockPoisoned,
}

impl SemanticIndexError {
    /// Stable machine-readable failure code.
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::EmptySnapshotVersion => "empty_snapshot_version",
            Self::EmptyModelIdentity => "empty_model_identity",
            Self::EmptyVectorDimension => "empty_vector_dimension",
            Self::EmptyCandidates => "empty_candidates",
            Self::PackedVectorByteLength { .. } => "packed_vector_byte_length",
            Self::NonFiniteVector { .. } => "non_finite_vector",
            Self::ZeroNormVector { .. } => "zero_norm_vector",
            Self::DuplicateCandidate { .. } => "duplicate_candidate",
            Self::ModelMismatch => "model_mismatch",
            Self::EmptyQueryBatch => "empty_query_batch",
            Self::DimensionMismatch { .. } => "dimension_mismatch",
            Self::EmptyAuthorization => "empty_authorization",
            Self::DuplicateAuthorization { .. } => "duplicate_authorization",
            Self::UnknownAuthorizedCandidate { .. } => "unknown_authorized_candidate",
            Self::MalformedPackedAuthorization => "malformed_packed_authorization",
            Self::NonUtf8PackedAuthorization => "non_utf8_packed_authorization",
            Self::SnapshotLockPoisoned => "snapshot_lock_poisoned",
        }
    }
}

impl fmt::Display for SemanticIndexError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.code())
    }
}

impl std::error::Error for SemanticIndexError {}

/// One immutable, exact, prevalidated semantic-unit snapshot.
#[derive(Clone, Debug)]
pub struct SemanticUnitIndex {
    evidence: SemanticIndexSnapshotEvidence,
    candidate_ids: Vec<(String, String)>,
    candidate_lookup: HashMap<String, HashMap<String, usize>>,
    normalized_vectors: Vec<f64>,
    vector_norms: Vec<f64>,
}

fn digest_bytes(domain: &[u8], values: impl IntoIterator<Item = impl AsRef<[u8]>>) -> String {
    let mut hasher = Sha256::new();
    hasher.update(domain);
    for value in values {
        let value = value.as_ref();
        hasher.update((value.len() as u64).to_be_bytes());
        hasher.update(value);
    }
    format!("sha256:{:x}", hasher.finalize())
}

fn update_length_prefixed(hasher: &mut Sha256, value: &[u8]) {
    hasher.update((value.len() as u64).to_be_bytes());
    hasher.update(value);
}

impl SemanticUnitIndex {
    /// Build an immutable exact index from canonical big-endian binary64 bytes.
    pub fn build(
        snapshot_version: &str,
        model_identity: &str,
        vector_dimension: usize,
        candidate_ids: Vec<(String, String)>,
        packed_vectors: &[u8],
    ) -> Result<Self, SemanticIndexError> {
        if snapshot_version.is_empty() {
            return Err(SemanticIndexError::EmptySnapshotVersion);
        }
        if model_identity.is_empty() {
            return Err(SemanticIndexError::EmptyModelIdentity);
        }
        if vector_dimension == 0 {
            return Err(SemanticIndexError::EmptyVectorDimension);
        }
        if candidate_ids.is_empty() {
            return Err(SemanticIndexError::EmptyCandidates);
        }
        let expected = candidate_ids
            .len()
            .checked_mul(vector_dimension)
            .and_then(|count| count.checked_mul(size_of::<f64>()))
            .unwrap_or(usize::MAX);
        if packed_vectors.len() != expected {
            return Err(SemanticIndexError::PackedVectorByteLength {
                expected,
                actual: packed_vectors.len(),
            });
        }

        let mut identities = HashSet::new();
        let mut candidate_lookup: HashMap<String, HashMap<String, usize>> =
            HashMap::with_capacity(candidate_ids.len());
        let mut normalized_vectors = Vec::with_capacity(candidate_ids.len() * vector_dimension);
        let mut vector_norms = Vec::with_capacity(candidate_ids.len());
        let vector_byte_count = vector_dimension * size_of::<f64>();
        for (index, (item_id, unit_id)) in candidate_ids.iter().enumerate() {
            if !identities.insert((item_id.clone(), unit_id.clone())) {
                return Err(SemanticIndexError::DuplicateCandidate {
                    item_id: (*item_id).to_owned(),
                    unit_id: (*unit_id).to_owned(),
                });
            }
            candidate_lookup
                .entry(item_id.clone())
                .or_default()
                .insert(unit_id.clone(), index);
            let start = index * vector_byte_count;
            let vector = packed_vectors[start..start + vector_byte_count]
                .chunks_exact(8)
                .map(|bytes| f64::from_be_bytes(bytes.try_into().expect("eight-byte chunk")))
                .collect::<Vec<_>>();
            let vector_label = format!("candidate vector for item {item_id:?}, unit {unit_id:?}");
            if vector.iter().any(|value| !value.is_finite()) {
                return Err(SemanticIndexError::NonFiniteVector { vector_label });
            }
            let scale = vector.iter().map(|value| value.abs()).fold(0.0, f64::max);
            if scale == 0.0 {
                return Err(SemanticIndexError::ZeroNormVector { vector_label });
            }
            let offset = normalized_vectors.len();
            normalized_vectors.extend(vector.iter().map(|value| value / scale));
            let norm = normalized_vectors[offset..]
                .iter()
                .map(|value| value * value)
                .sum::<f64>()
                .sqrt();
            vector_norms.push(norm);
        }

        let model_digest = digest_bytes(
            b"rankweave.semantic-unit-index.model.v1\0",
            [model_identity.as_bytes()],
        );
        let dimension_bytes = (vector_dimension as u64).to_be_bytes();
        let dimension_digest = digest_bytes(
            b"rankweave.semantic-unit-index.dimension.v1\0",
            [dimension_bytes],
        );
        let mut vector_hasher = Sha256::new();
        vector_hasher.update(b"rankweave.semantic-unit-index.vectors.v1\0");
        vector_hasher.update((candidate_ids.len() as u64).to_be_bytes());
        for (index, (item_id, unit_id)) in candidate_ids.iter().enumerate() {
            update_length_prefixed(&mut vector_hasher, item_id.as_bytes());
            update_length_prefixed(&mut vector_hasher, unit_id.as_bytes());
            vector_hasher.update((vector_dimension as u64).to_be_bytes());
            let start = index * vector_byte_count;
            vector_hasher.update(&packed_vectors[start..start + vector_byte_count]);
        }
        let vectors_digest = format!("sha256:{:x}", vector_hasher.finalize());
        let snapshot_digest = digest_bytes(
            b"rankweave.semantic-unit-index.snapshot.v1\0",
            [
                snapshot_version.as_bytes(),
                model_digest.as_bytes(),
                dimension_digest.as_bytes(),
                vectors_digest.as_bytes(),
            ],
        );
        let evidence = SemanticIndexSnapshotEvidence {
            schema_version: SEMANTIC_INDEX_SNAPSHOT_SCHEMA_VERSION,
            snapshot_version: snapshot_version.to_owned(),
            model_digest,
            dimension_digest,
            vectors_digest,
            snapshot_digest,
            vector_dimension,
            candidate_count: candidate_ids.len(),
        };
        Ok(Self {
            evidence,
            candidate_ids,
            candidate_lookup,
            normalized_vectors,
            vector_norms,
        })
    }

    /// Return immutable snapshot integrity evidence.
    #[must_use]
    pub fn evidence(&self) -> &SemanticIndexSnapshotEvidence {
        &self.evidence
    }

    /// Rank only the caller-authorized candidate identities with exact cosine.
    pub fn rank_authorized(
        &self,
        model_identity: &str,
        query_vector: &[f64],
        authorized_candidate_ids: &[(String, String)],
    ) -> Result<SemanticIndexRankingReport, SemanticIndexError> {
        let authorized_refs = authorized_candidate_ids
            .iter()
            .map(|(item_id, unit_id)| (item_id.as_str(), unit_id.as_str()))
            .collect::<Vec<_>>();
        self.rank_authorized_refs(model_identity, query_vector, &authorized_refs)
    }

    fn rank_authorized_refs(
        &self,
        model_identity: &str,
        query_vector: &[f64],
        authorized_candidate_ids: &[(&str, &str)],
    ) -> Result<SemanticIndexRankingReport, SemanticIndexError> {
        let model_digest = digest_bytes(
            b"rankweave.semantic-unit-index.model.v1\0",
            [model_identity.as_bytes()],
        );
        if model_digest != self.evidence.model_digest {
            return Err(SemanticIndexError::ModelMismatch);
        }
        if authorized_candidate_ids.is_empty() {
            return Err(SemanticIndexError::EmptyAuthorization);
        }
        let mut authorization_seen = HashSet::new();
        let mut authorized_indices = Vec::with_capacity(authorized_candidate_ids.len());
        for (item_id, unit_id) in authorized_candidate_ids {
            if !authorization_seen.insert((item_id, unit_id)) {
                return Err(SemanticIndexError::DuplicateAuthorization {
                    item_id: (*item_id).to_owned(),
                    unit_id: (*unit_id).to_owned(),
                });
            }
            let Some(index) = self
                .candidate_lookup
                .get(*item_id)
                .and_then(|units| units.get(*unit_id))
            else {
                return Err(SemanticIndexError::UnknownAuthorizedCandidate {
                    item_id: (*item_id).to_owned(),
                    unit_id: (*unit_id).to_owned(),
                });
            };
            authorized_indices.push(*index);
        }
        let query = self.prepare_query(query_vector)?;
        let dimension = self.evidence.vector_dimension;
        let scored = authorized_indices
            .par_iter()
            .map(|index| {
                let start = index * dimension;
                let dot = query
                    .normalized
                    .iter()
                    .zip(&self.normalized_vectors[start..start + dimension])
                    .fold(0.0, |sum, (left, right)| sum + left * right);
                let score = (dot / (query.norm * self.vector_norms[*index])).clamp(0.0, 1.0);
                (*index, score)
            })
            .collect::<Vec<_>>();
        let mut best_by_item = HashMap::new();
        for (index, score) in scored {
            let (item_id, unit_id) = &self.candidate_ids[index];
            retain_best_unit(&mut best_by_item, item_id, unit_id, score);
        }
        Ok(self.finish_query_report(
            &model_digest,
            query_vector,
            authorized_candidate_ids,
            best_by_item,
        ))
    }

    fn rank_authorized_batch_refs(
        &self,
        model_identity: &str,
        query_vectors: &[&[f64]],
        authorized_candidate_ids: &[(&str, &str)],
    ) -> Result<Vec<SemanticIndexRankingReport>, SemanticIndexError> {
        let model_digest = digest_bytes(
            b"rankweave.semantic-unit-index.model.v1\0",
            [model_identity.as_bytes()],
        );
        if model_digest != self.evidence.model_digest {
            return Err(SemanticIndexError::ModelMismatch);
        }
        if query_vectors.is_empty() {
            return Err(SemanticIndexError::EmptyQueryBatch);
        }
        if authorized_candidate_ids.is_empty() {
            return Err(SemanticIndexError::EmptyAuthorization);
        }
        let mut authorization_seen = HashSet::new();
        let mut authorized_indices = Vec::with_capacity(authorized_candidate_ids.len());
        for (item_id, unit_id) in authorized_candidate_ids {
            if !authorization_seen.insert((item_id, unit_id)) {
                return Err(SemanticIndexError::DuplicateAuthorization {
                    item_id: (*item_id).to_owned(),
                    unit_id: (*unit_id).to_owned(),
                });
            }
            let Some(index) = self
                .candidate_lookup
                .get(*item_id)
                .and_then(|units| units.get(*unit_id))
            else {
                return Err(SemanticIndexError::UnknownAuthorizedCandidate {
                    item_id: (*item_id).to_owned(),
                    unit_id: (*unit_id).to_owned(),
                });
            };
            authorized_indices.push(*index);
        }

        let prepared_queries = query_vectors
            .iter()
            .map(|query_vector| self.prepare_query(query_vector))
            .collect::<Result<Vec<_>, _>>()?;
        let mut unique_query_indices = Vec::new();
        let mut original_to_unique = Vec::with_capacity(query_vectors.len());
        for (query_index, query_vector) in query_vectors.iter().enumerate() {
            let existing = unique_query_indices.iter().position(|unique_index| {
                vectors_have_identical_bits(query_vectors[*unique_index], query_vector)
            });
            original_to_unique.push(existing.unwrap_or_else(|| {
                unique_query_indices.push(query_index);
                unique_query_indices.len() - 1
            }));
        }
        let unique_queries = unique_query_indices
            .iter()
            .map(|index| &prepared_queries[*index])
            .collect::<Vec<_>>();
        let dimension = self.evidence.vector_dimension;
        let query_count = unique_queries.len();
        let mut normalized_queries_by_coordinate = Vec::new();
        for coordinate in 0..dimension {
            normalized_queries_by_coordinate.extend(
                unique_queries
                    .iter()
                    .map(|query| query.normalized[coordinate]),
            );
        }
        let best_by_query = authorized_indices
            .par_iter()
            .fold(
                || (vec![0.0; query_count], empty_best_maps(query_count)),
                |(mut dots, mut best_by_query), index| {
                    dots.fill(0.0);
                    let start = index * dimension;
                    for coordinate in 0..dimension {
                        let candidate_value = self.normalized_vectors[start + coordinate];
                        let query_start = coordinate * query_count;
                        for (dot, query_value) in dots.iter_mut().zip(
                            &normalized_queries_by_coordinate
                                [query_start..query_start + query_count],
                        ) {
                            *dot += query_value * candidate_value;
                        }
                    }
                    let (item_id, unit_id) = &self.candidate_ids[*index];
                    for (query_index, query) in unique_queries.iter().enumerate() {
                        let score = (dots[query_index] / (query.norm * self.vector_norms[*index]))
                            .clamp(0.0, 1.0);
                        retain_best_unit(&mut best_by_query[query_index], item_id, unit_id, score);
                    }
                    (dots, best_by_query)
                },
            )
            .map(|(_, best_by_query)| best_by_query)
            .reduce(
                || empty_best_maps(query_count),
                |mut left, right| {
                    for (left_query, right_query) in left.iter_mut().zip(right) {
                        for result in right_query.into_values() {
                            retain_best_unit(
                                left_query,
                                &result.item_id,
                                &result.winning_unit_id,
                                result.score,
                            );
                        }
                    }
                    left
                },
            );

        let unique_reports = unique_query_indices
            .iter()
            .zip(best_by_query)
            .map(|(query_index, best_by_item)| {
                self.finish_query_report(
                    &model_digest,
                    query_vectors[*query_index],
                    authorized_candidate_ids,
                    best_by_item,
                )
            })
            .collect::<Vec<_>>();
        Ok(original_to_unique
            .into_iter()
            .map(|unique_index| unique_reports[unique_index].clone())
            .collect())
    }

    fn prepare_query(&self, query_vector: &[f64]) -> Result<PreparedQuery, SemanticIndexError> {
        if query_vector.len() != self.evidence.vector_dimension {
            return Err(SemanticIndexError::DimensionMismatch {
                expected: self.evidence.vector_dimension,
                actual: query_vector.len(),
            });
        }
        if query_vector.iter().any(|value| !value.is_finite()) {
            return Err(SemanticIndexError::NonFiniteVector {
                vector_label: "query vector".to_owned(),
            });
        }
        let query_scale = query_vector
            .iter()
            .map(|value| value.abs())
            .fold(0.0, f64::max);
        if query_scale == 0.0 {
            return Err(SemanticIndexError::ZeroNormVector {
                vector_label: "query vector".to_owned(),
            });
        }
        let normalized = query_vector
            .iter()
            .map(|value| value / query_scale)
            .collect::<Vec<_>>();
        let norm = normalized
            .iter()
            .map(|value| value * value)
            .sum::<f64>()
            .sqrt();
        Ok(PreparedQuery { normalized, norm })
    }

    fn finish_query_report(
        &self,
        model_digest: &str,
        query_vector: &[f64],
        authorized_candidate_ids: &[(&str, &str)],
        best_by_item: HashMap<String, SemanticUnitRank>,
    ) -> SemanticIndexRankingReport {
        let mut results = best_by_item.into_values().collect::<Vec<_>>();
        results.sort_by(|left, right| {
            right
                .score
                .total_cmp(&left.score)
                .then_with(|| left.item_id.cmp(&right.item_id))
        });

        let mut input_hasher = Sha256::new();
        input_hasher.update(b"rankweave.semantic-unit-index.query.v1\0");
        update_length_prefixed(&mut input_hasher, self.evidence.snapshot_digest.as_bytes());
        update_length_prefixed(&mut input_hasher, model_digest.as_bytes());
        input_hasher.update((query_vector.len() as u64).to_be_bytes());
        for value in query_vector {
            input_hasher.update(value.to_bits().to_be_bytes());
        }
        input_hasher.update((authorized_candidate_ids.len() as u64).to_be_bytes());
        for (item_id, unit_id) in authorized_candidate_ids {
            update_length_prefixed(&mut input_hasher, item_id.as_bytes());
            update_length_prefixed(&mut input_hasher, unit_id.as_bytes());
        }
        let ordered_input_digest = format!("sha256:{:x}", input_hasher.finalize());

        let mut output_hasher = Sha256::new();
        output_hasher.update(b"rankweave.semantic-unit-index.result.v1\0");
        output_hasher.update((results.len() as u64).to_be_bytes());
        for result in &results {
            update_length_prefixed(&mut output_hasher, result.item_id.as_bytes());
            update_length_prefixed(&mut output_hasher, result.winning_unit_id.as_bytes());
            output_hasher.update(result.score.to_bits().to_be_bytes());
        }
        let output_digest = format!("sha256:{:x}", output_hasher.finalize());
        SemanticIndexRankingReport {
            snapshot: self.evidence.clone(),
            algorithm_version: SEMANTIC_UNIT_COSINE_ALGORITHM_VERSION,
            execution_profile: SEMANTIC_INDEX_CPU_EXECUTION_PROFILE,
            worker_count: rayon::current_num_threads(),
            ordered_input_digest,
            output_digest,
            results,
        }
    }

    /// Rank ordered queries against one identical canonical packed authorization.
    pub fn rank_authorized_batch_packed(
        &self,
        model_identity: &str,
        query_vectors: &[Vec<f64>],
        packed_authorization: &[u8],
    ) -> Result<Vec<SemanticIndexRankingReport>, SemanticIndexError> {
        let authorized = parse_packed_authorization(packed_authorization)?;
        let query_refs = query_vectors.iter().map(Vec::as_slice).collect::<Vec<_>>();
        self.rank_authorized_batch_refs(model_identity, &query_refs, &authorized)
    }

    /*
        The single-query packed API remains the stable compatibility surface;
        parsing delegates to the same borrowed authorization representation as
        the batch operation.
    */
    fn rank_authorized_packed_inner(
        &self,
        model_identity: &str,
        query_vector: &[f64],
        packed_authorization: &[u8],
    ) -> Result<SemanticIndexRankingReport, SemanticIndexError> {
        let authorized = parse_packed_authorization(packed_authorization)?;
        self.rank_authorized_refs(model_identity, query_vector, &authorized)
    }

    /// Rank a canonical packed ordered authorization set without Python rows.
    pub fn rank_authorized_packed(
        &self,
        model_identity: &str,
        query_vector: &[f64],
        packed_authorization: &[u8],
    ) -> Result<SemanticIndexRankingReport, SemanticIndexError> {
        self.rank_authorized_packed_inner(model_identity, query_vector, packed_authorization)
    }

    /// Exercise exact scoring for one real packed authorization scope.
    ///
    /// The query is the first authorized candidate vector already owned by
    /// this immutable snapshot. This keeps vector arithmetic in Rust while
    /// forcing authorization parsing, the complete exact matrix traversal,
    /// stable per-item reduction, and report digest construction before a
    /// caller advertises readiness. Readiness callers discard the report.
    pub fn preflight_authorized_packed(
        &self,
        model_identity: &str,
        packed_authorization: &[u8],
    ) -> Result<SemanticIndexRankingReport, SemanticIndexError> {
        let model_digest = digest_bytes(
            b"rankweave.semantic-unit-index.model.v1\0",
            [model_identity.as_bytes()],
        );
        if model_digest != self.evidence.model_digest {
            return Err(SemanticIndexError::ModelMismatch);
        }
        let authorized = parse_packed_authorization(packed_authorization)?;
        let Some((item_id, unit_id)) = authorized.first() else {
            return Err(SemanticIndexError::EmptyAuthorization);
        };
        let Some(index) = self
            .candidate_lookup
            .get(*item_id)
            .and_then(|units| units.get(*unit_id))
        else {
            return Err(SemanticIndexError::UnknownAuthorizedCandidate {
                item_id: (*item_id).to_owned(),
                unit_id: (*unit_id).to_owned(),
            });
        };
        let start = index * self.evidence.vector_dimension;
        let query = self.normalized_vectors[start..start + self.evidence.vector_dimension].to_vec();
        self.rank_authorized_refs(model_identity, &query, &authorized)
    }
}

struct PreparedQuery {
    normalized: Vec<f64>,
    norm: f64,
}

fn vectors_have_identical_bits(left: &[f64], right: &[f64]) -> bool {
    left.len() == right.len()
        && left
            .iter()
            .zip(right)
            .all(|(left, right)| left.to_bits() == right.to_bits())
}

fn empty_best_maps(query_count: usize) -> Vec<HashMap<String, SemanticUnitRank>> {
    (0..query_count).map(|_| HashMap::new()).collect()
}

fn retain_best_unit(
    best_by_item: &mut HashMap<String, SemanticUnitRank>,
    item_id: &str,
    unit_id: &str,
    score: f64,
) {
    let proposed = SemanticUnitRank {
        item_id: item_id.to_owned(),
        winning_unit_id: unit_id.to_owned(),
        score,
    };
    best_by_item
        .entry(item_id.to_owned())
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

fn parse_packed_authorization(
    packed_authorization: &[u8],
) -> Result<Vec<(&str, &str)>, SemanticIndexError> {
    let mut cursor = 0_usize;
    let count = read_packed_u64(packed_authorization, &mut cursor)?;
    if count > ((packed_authorization.len() - cursor) / 16) as u64 {
        return Err(SemanticIndexError::MalformedPackedAuthorization);
    }
    let count = count as usize;
    let mut authorized = Vec::with_capacity(count);
    for _ in 0..count {
        let item = read_packed_text(packed_authorization, &mut cursor)?;
        let unit = read_packed_text(packed_authorization, &mut cursor)?;
        authorized.push((item, unit));
    }
    if cursor != packed_authorization.len() {
        return Err(SemanticIndexError::MalformedPackedAuthorization);
    }
    Ok(authorized)
}

fn read_packed_u64(bytes: &[u8], cursor: &mut usize) -> Result<u64, SemanticIndexError> {
    let end = *cursor + 8;
    let value = bytes
        .get(*cursor..end)
        .ok_or(SemanticIndexError::MalformedPackedAuthorization)?;
    *cursor = end;
    Ok(u64::from_be_bytes(
        value.try_into().expect("eight-byte packed integer"),
    ))
}

fn read_packed_text<'a>(
    bytes: &'a [u8],
    cursor: &mut usize,
) -> Result<&'a str, SemanticIndexError> {
    let length = read_packed_u64(bytes, cursor)?;
    if length > (bytes.len() - *cursor) as u64 {
        return Err(SemanticIndexError::MalformedPackedAuthorization);
    }
    let length = length as usize;
    let end = *cursor + length;
    let value = &bytes[*cursor..end];
    *cursor = end;
    std::str::from_utf8(value).map_err(|_| SemanticIndexError::NonUtf8PackedAuthorization)
}

/// Atomically replace an immutable exact index only after successful validation.
pub struct SemanticUnitIndexHandle {
    current: RwLock<Arc<SemanticUnitIndex>>,
}

impl SemanticUnitIndexHandle {
    /// Create a handle from one fully validated snapshot.
    #[must_use]
    pub fn new(index: SemanticUnitIndex) -> Self {
        Self {
            current: RwLock::new(Arc::new(index)),
        }
    }

    /// Replace the current snapshot atomically after the caller builds it fully.
    pub fn replace(&self, index: SemanticUnitIndex) -> Result<(), SemanticIndexError> {
        let mut current = self
            .current
            .write()
            .map_err(|_| SemanticIndexError::SnapshotLockPoisoned)?;
        *current = Arc::new(index);
        Ok(())
    }

    /// Acquire one immutable snapshot for a complete query.
    pub fn snapshot(&self) -> Result<Arc<SemanticUnitIndex>, SemanticIndexError> {
        self.current
            .read()
            .map(|current| Arc::clone(&current))
            .map_err(|_| SemanticIndexError::SnapshotLockPoisoned)
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use std::thread;

    use super::{SemanticIndexError, SemanticUnitIndex, SemanticUnitIndexHandle};
    use crate::{SemanticUnitCandidate, rank_semantic_units};
    use rayon::ThreadPoolBuilder;

    fn packed(vectors: &[&[f64]]) -> Vec<u8> {
        vectors
            .iter()
            .flat_map(|vector| vector.iter())
            .flat_map(|value| value.to_be_bytes())
            .collect()
    }

    fn packed_authorization(identities: &[(String, String)]) -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(&(identities.len() as u64).to_be_bytes());
        for (item_id, unit_id) in identities {
            bytes.extend_from_slice(&(item_id.len() as u64).to_be_bytes());
            bytes.extend_from_slice(item_id.as_bytes());
            bytes.extend_from_slice(&(unit_id.len() as u64).to_be_bytes());
            bytes.extend_from_slice(unit_id.as_bytes());
        }
        bytes
    }

    fn index(version: &str) -> SemanticUnitIndex {
        SemanticUnitIndex::build(
            version,
            "model-v1",
            2,
            vec![
                ("item-b".to_owned(), "unit-z".to_owned()),
                ("item-a".to_owned(), "unit-z".to_owned()),
                ("item-a".to_owned(), "unit-a".to_owned()),
            ],
            &packed(&[&[1.0, 0.0], &[1.0, 0.0], &[0.0, 1.0]]),
        )
        .unwrap()
    }

    #[test]
    fn snapshot_evidence_and_authorized_results_are_exact() {
        let index = index("snapshot-v1");
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let report = index
            .rank_authorized("model-v1", &[1.0, 0.0], &authorization)
            .unwrap();

        assert_eq!(report.snapshot.snapshot_version, "snapshot-v1");
        assert_eq!(report.snapshot.vector_dimension, 2);
        assert_eq!(report.snapshot.candidate_count, 3);
        assert!(report.snapshot.snapshot_digest.starts_with("sha256:"));
        assert!(report.ordered_input_digest.starts_with("sha256:"));
        assert!(report.output_digest.starts_with("sha256:"));
        assert_eq!(report.results.len(), 2);
        assert_eq!(report.results[0].item_id, "item-a");
        assert_eq!(report.results[0].winning_unit_id, "unit-z");
        assert_eq!(report.results[1].item_id, "item-b");
    }

    #[test]
    fn worker_count_does_not_change_exact_result_or_digests() {
        let index = index("snapshot-v1");
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let run = |worker_count| {
            ThreadPoolBuilder::new()
                .num_threads(worker_count)
                .build()
                .unwrap()
                .install(|| {
                    index
                        .rank_authorized("model-v1", &[1.0, 0.0], &authorization)
                        .unwrap()
                })
        };
        let one_worker = run(1);
        let four_workers = run(4);

        assert_eq!(one_worker.results, four_workers.results);
        assert_eq!(
            one_worker.ordered_input_digest,
            four_workers.ordered_input_digest
        );
        assert_eq!(one_worker.output_digest, four_workers.output_digest);
        assert_eq!(one_worker.worker_count, 1);
        assert_eq!(four_workers.worker_count, 4);
    }

    #[test]
    fn packed_authorization_preserves_exact_results_and_digests() {
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let index = index("snapshot-v1");
        let rows = index
            .rank_authorized("model-v1", &[1.0, 0.0], &authorization)
            .unwrap();
        let packed = index
            .rank_authorized_packed(
                "model-v1",
                &[1.0, 0.0],
                &packed_authorization(&authorization),
            )
            .unwrap();

        assert_eq!(packed.results, rows.results);
        assert_eq!(packed.ordered_input_digest, rows.ordered_input_digest);
        assert_eq!(packed.output_digest, rows.output_digest);
    }

    #[test]
    fn packed_preflight_exercises_one_real_authorization_scope() {
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let index = index("snapshot-v1");

        let report = index
            .preflight_authorized_packed("model-v1", &packed_authorization(&authorization))
            .unwrap();

        assert_eq!(report.snapshot, *index.evidence());
        assert_eq!(report.results.len(), 2);
        assert_eq!(report.results[0].item_id, "item-a");
        assert_eq!(report.results[1].item_id, "item-b");
        assert!(report.ordered_input_digest.starts_with("sha256:"));
        assert!(report.output_digest.starts_with("sha256:"));
    }

    #[test]
    fn packed_preflight_rejects_empty_and_unknown_scopes() {
        let index = index("snapshot-v1");
        let cases = [
            index.preflight_authorized_packed(
                "other-model",
                &packed_authorization(&[("missing".to_owned(), "unit".to_owned())]),
            ),
            index.preflight_authorized_packed("model-v1", b"short"),
            index.preflight_authorized_packed("model-v1", &packed_authorization(&[])),
            index.preflight_authorized_packed(
                "model-v1",
                &packed_authorization(&[("missing".to_owned(), "unit".to_owned())]),
            ),
        ];

        assert_eq!(cases[0].as_ref().unwrap_err().code(), "model_mismatch");
        assert_eq!(
            cases[1].as_ref().unwrap_err().code(),
            "malformed_packed_authorization"
        );
        assert_eq!(cases[2].as_ref().unwrap_err().code(), "empty_authorization");
        assert_eq!(
            cases[3].as_ref().unwrap_err().code(),
            "unknown_authorized_candidate"
        );
    }

    #[test]
    fn packed_batch_matches_every_independent_query_and_digest() {
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let packed_authorization = packed_authorization(&authorization);
        let queries = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![1.0, 1.0],
            vec![1.0, 0.0],
        ];
        let index = index("snapshot-v1");

        let batch = index
            .rank_authorized_batch_packed("model-v1", &queries, &packed_authorization)
            .unwrap();
        let independent = queries
            .iter()
            .map(|query| {
                index
                    .rank_authorized_packed("model-v1", query, &packed_authorization)
                    .unwrap()
            })
            .collect::<Vec<_>>();

        assert_eq!(batch, independent);
    }

    #[test]
    fn packed_batch_validation_failures_are_explicit() {
        let index = index("snapshot-v1");
        let known = ("item-a".to_owned(), "unit-a".to_owned());
        let cases = [
            index.rank_authorized_batch_packed(
                "other-model",
                &[vec![1.0, 0.0]],
                &packed_authorization(std::slice::from_ref(&known)),
            ),
            index.rank_authorized_batch_packed(
                "model-v1",
                &[vec![1.0, 0.0]],
                &packed_authorization(&[]),
            ),
            index.rank_authorized_batch_packed(
                "model-v1",
                &[vec![1.0, 0.0]],
                &packed_authorization(&[known.clone(), known.clone()]),
            ),
            index.rank_authorized_batch_packed(
                "model-v1",
                &[vec![1.0, 0.0]],
                &packed_authorization(&[("missing".to_owned(), "unit".to_owned())]),
            ),
            index.rank_authorized_batch_packed(
                "model-v1",
                &[vec![1.0]],
                &packed_authorization(std::slice::from_ref(&known)),
            ),
        ];
        let codes = [
            "model_mismatch",
            "empty_authorization",
            "duplicate_authorization",
            "unknown_authorized_candidate",
            "dimension_mismatch",
        ];
        for (result, code) in cases.into_iter().zip(codes) {
            assert_eq!(result.unwrap_err().code(), code);
        }
    }

    #[test]
    fn malformed_packed_authorization_fails_closed() {
        let index = index("snapshot-v1");
        assert_eq!(
            index
                .rank_authorized_batch_packed("model-v1", &[vec![1.0, 0.0]], b"short")
                .unwrap_err()
                .code(),
            "malformed_packed_authorization"
        );
        let cases = [
            (&b"short"[..], "malformed_packed_authorization"),
            (
                &[0, 0, 0, 0, 0, 0, 0, 1][..],
                "malformed_packed_authorization",
            ),
            (
                &[
                    0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 9, b'a', b'a', b'a', b'a', b'a',
                    b'a', b'a', b'a',
                ][..],
                "malformed_packed_authorization",
            ),
            (
                &[
                    0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, b'a', b'a', 0, 0, 0, 0, 0, 0, 0,
                ][..],
                "malformed_packed_authorization",
            ),
            (
                &[
                    0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0xff, 0, 0, 0, 0, 0, 0, 0, 0,
                ][..],
                "non_utf8_packed_authorization",
            ),
        ];
        for (bytes, code) in cases {
            assert_eq!(
                index
                    .rank_authorized_packed("model-v1", &[1.0, 0.0], bytes)
                    .unwrap_err()
                    .code(),
                code
            );
        }
        let mut trailing = packed_authorization(&[("item-a".to_owned(), "unit-a".to_owned())]);
        trailing.push(0);
        assert_eq!(
            index
                .rank_authorized_packed("model-v1", &[1.0, 0.0], &trailing)
                .unwrap_err()
                .code(),
            "malformed_packed_authorization"
        );
    }

    #[test]
    fn authorization_never_returns_an_unlisted_candidate() {
        let report = index("snapshot-v1")
            .rank_authorized(
                "model-v1",
                &[1.0, 0.0],
                &[("item-a".to_owned(), "unit-a".to_owned())],
            )
            .unwrap();

        assert_eq!(report.results.len(), 1);
        assert_eq!(report.results[0].item_id, "item-a");
        assert_eq!(report.results[0].winning_unit_id, "unit-a");
    }

    #[test]
    fn indexed_scores_equal_the_existing_exact_cosine_contract() {
        let ids = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let vectors = [&[0.25, -0.5, 0.75][..], &[0.3, 0.2, 0.1], &[-0.4, 0.7, 0.2]];
        let query = [0.5, -0.25, 0.75];
        let indexed =
            SemanticUnitIndex::build("snapshot-v1", "model-v1", 3, ids.clone(), &packed(&vectors))
                .unwrap()
                .rank_authorized("model-v1", &query, &ids)
                .unwrap();
        let scalar_candidates = ids
            .iter()
            .zip(vectors)
            .map(|((item_id, unit_id), vector)| SemanticUnitCandidate {
                item_id: item_id.clone(),
                unit_id: unit_id.clone(),
                vector: vector.to_vec(),
            })
            .collect::<Vec<_>>();
        let scalar = rank_semantic_units(&query, &scalar_candidates).unwrap();

        assert_eq!(indexed.results, scalar.results);
    }

    #[test]
    fn exact_ties_choose_the_lexicographically_first_unit() {
        let ids = vec![
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let report = SemanticUnitIndex::build(
            "snapshot-v1",
            "model-v1",
            2,
            ids.clone(),
            &packed(&[&[1.0, 0.0], &[1.0, 0.0]]),
        )
        .unwrap()
        .rank_authorized("model-v1", &[1.0, 0.0], &ids)
        .unwrap();

        assert_eq!(report.results[0].winning_unit_id, "unit-a");
    }

    #[test]
    fn cold_rebuild_preserves_snapshot_and_result_digests() {
        let authorization = vec![
            ("item-b".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-z".to_owned()),
            ("item-a".to_owned(), "unit-a".to_owned()),
        ];
        let first = index("snapshot-v1");
        let restarted = index("snapshot-v1");
        let first_report = first
            .rank_authorized("model-v1", &[1.0, 0.0], &authorization)
            .unwrap();
        let restarted_report = restarted
            .rank_authorized("model-v1", &[1.0, 0.0], &authorization)
            .unwrap();

        assert_eq!(first.evidence(), restarted.evidence());
        assert_eq!(first_report.results, restarted_report.results);
        assert_eq!(
            first_report.ordered_input_digest,
            restarted_report.ordered_input_digest
        );
        assert_eq!(first_report.output_digest, restarted_report.output_digest);
    }

    #[test]
    fn invalid_snapshot_and_query_inputs_fail_closed() {
        let ids = vec![("item".to_owned(), "unit".to_owned())];
        let valid_bytes = packed(&[&[1.0]]);
        let build_cases = [
            SemanticUnitIndex::build("", "model", 1, ids.clone(), &valid_bytes),
            SemanticUnitIndex::build("snapshot", "", 1, ids.clone(), &valid_bytes),
            SemanticUnitIndex::build("snapshot", "model", 0, ids.clone(), &[]),
            SemanticUnitIndex::build("snapshot", "model", 1, vec![], &[]),
            SemanticUnitIndex::build("snapshot", "model", 1, ids.clone(), b"short"),
            SemanticUnitIndex::build("snapshot", "model", 1, ids.clone(), &packed(&[&[f64::NAN]])),
            SemanticUnitIndex::build("snapshot", "model", 1, ids.clone(), &packed(&[&[0.0]])),
            SemanticUnitIndex::build(
                "snapshot",
                "model",
                1,
                vec![ids[0].clone(), ids[0].clone()],
                &packed(&[&[1.0], &[1.0]]),
            ),
        ];
        let build_codes = [
            "empty_snapshot_version",
            "empty_model_identity",
            "empty_vector_dimension",
            "empty_candidates",
            "packed_vector_byte_length",
            "non_finite_vector",
            "zero_norm_vector",
            "duplicate_candidate",
        ];
        for (result, code) in build_cases.into_iter().zip(build_codes) {
            assert_eq!(result.unwrap_err().code(), code);
        }

        let index =
            SemanticUnitIndex::build("snapshot", "model", 1, ids.clone(), &valid_bytes).unwrap();
        let rank_cases = [
            index.rank_authorized("other", &[1.0], &ids),
            index.rank_authorized("model", &[1.0, 0.0], &ids),
            index.rank_authorized("model", &[f64::NAN], &ids),
            index.rank_authorized("model", &[0.0], &ids),
            index.rank_authorized("model", &[1.0], &[]),
            index.rank_authorized("model", &[1.0], &[ids[0].clone(), ids[0].clone()]),
            index.rank_authorized(
                "model",
                &[1.0],
                &[("missing".to_owned(), "unit".to_owned())],
            ),
        ];
        let rank_codes = [
            "model_mismatch",
            "dimension_mismatch",
            "non_finite_vector",
            "zero_norm_vector",
            "empty_authorization",
            "duplicate_authorization",
            "unknown_authorized_candidate",
        ];
        for (result, code) in rank_cases.into_iter().zip(rank_codes) {
            assert_eq!(result.unwrap_err().code(), code);
        }
        assert_eq!(
            index
                .rank_authorized_batch_packed("model", &[], &packed_authorization(&ids),)
                .unwrap_err()
                .code(),
            "empty_query_batch"
        );
    }

    #[test]
    fn snapshot_replacement_is_atomic_and_failed_build_preserves_current() {
        let handle = SemanticUnitIndexHandle::new(index("snapshot-v1"));
        let in_flight_snapshot = handle.snapshot().unwrap();
        let invalid = SemanticUnitIndex::build(
            "snapshot-v2",
            "model-v1",
            2,
            vec![("item".to_owned(), "unit".to_owned())],
            b"short",
        );
        assert!(invalid.is_err());
        assert_eq!(
            handle.snapshot().unwrap().evidence().snapshot_version,
            "snapshot-v1"
        );

        handle.replace(index("snapshot-v2")).unwrap();
        assert_eq!(
            handle.snapshot().unwrap().evidence().snapshot_version,
            "snapshot-v2"
        );
        assert_eq!(
            in_flight_snapshot.evidence().snapshot_version,
            "snapshot-v1"
        );
    }

    #[test]
    fn poisoned_snapshot_lock_fails_closed() {
        let handle = Arc::new(SemanticUnitIndexHandle::new(index("snapshot-v1")));
        let poisoned = Arc::clone(&handle);
        assert!(
            thread::spawn(move || {
                let _guard = poisoned.current.write().unwrap();
                panic!("synthetic lock poison");
            })
            .join()
            .is_err()
        );

        assert_eq!(
            handle.snapshot().unwrap_err(),
            SemanticIndexError::SnapshotLockPoisoned
        );
        assert_eq!(
            handle.replace(index("snapshot-v2")).unwrap_err(),
            SemanticIndexError::SnapshotLockPoisoned
        );
    }

    #[test]
    fn error_display_is_the_stable_code() {
        for error in [
            SemanticIndexError::ModelMismatch,
            SemanticIndexError::EmptyQueryBatch,
            SemanticIndexError::SnapshotLockPoisoned,
        ] {
            assert_eq!(error.to_string(), error.code());
        }
    }
}
