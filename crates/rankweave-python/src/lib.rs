//! Python bindings for the RankWeave calculation core.

use num_bigint::BigUint;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use rankweave_core::semantic_index::{
    SemanticIndexRankingReport, SemanticIndexSnapshotEvidence,
    SemanticUnitIndex as CoreSemanticUnitIndex, SemanticUnitIndexHandle,
};

#[pyfunction]
fn theoretical_min_max_normalize(score: f64, lower: f64, upper: f64) -> f64 {
    rankweave_core::theoretical_min_max_normalize(score, lower, upper)
}

#[pyfunction]
fn convex_combination_score(
    semantic_score: Option<f64>,
    lexical_score: Option<f64>,
    semantic_weight_alpha: f64,
) -> f64 {
    rankweave_core::convex_combination_score(semantic_score, lexical_score, semantic_weight_alpha)
}

#[pyfunction]
fn reciprocal_rank_fusion_score(ranks: Vec<BigUint>, rank_constant_eta: BigUint) -> f64 {
    rankweave_core::reciprocal_rank_fusion_score(&ranks, &rank_constant_eta)
}

type SemanticUnitReportTuple = (String, String, String, usize, Vec<(String, String, f64)>);
type SemanticIndexEvidenceTuple = (String, String, String, String, String, String, usize, usize);
type SemanticIndexReportTuple = (
    SemanticIndexEvidenceTuple,
    String,
    String,
    usize,
    String,
    String,
    Vec<(String, String, f64)>,
);

fn index_error(error: rankweave_core::semantic_index::SemanticIndexError) -> PyErr {
    PyValueError::new_err(format!(
        "{}: exact semantic index rejected input ({error:?})",
        error.code()
    ))
}

fn evidence_tuple(evidence: &SemanticIndexSnapshotEvidence) -> SemanticIndexEvidenceTuple {
    (
        evidence.schema_version.to_owned(),
        evidence.snapshot_version.clone(),
        evidence.model_digest.clone(),
        evidence.dimension_digest.clone(),
        evidence.vectors_digest.clone(),
        evidence.snapshot_digest.clone(),
        evidence.vector_dimension,
        evidence.candidate_count,
    )
}

fn index_report_tuple(report: SemanticIndexRankingReport) -> SemanticIndexReportTuple {
    (
        evidence_tuple(&report.snapshot),
        report.algorithm_version.to_owned(),
        report.execution_profile.to_owned(),
        report.worker_count,
        report.ordered_input_digest,
        report.output_digest,
        report
            .results
            .into_iter()
            .map(|result| (result.item_id, result.winning_unit_id, result.score))
            .collect(),
    )
}

#[pyclass]
struct SemanticUnitIndex {
    handle: SemanticUnitIndexHandle,
}

#[pymethods]
impl SemanticUnitIndex {
    #[new]
    fn new(
        snapshot_version: &str,
        model_identity: &str,
        vector_dimension: usize,
        candidate_ids: Vec<(String, String)>,
        packed_vectors: &Bound<'_, PyBytes>,
    ) -> PyResult<Self> {
        let index = CoreSemanticUnitIndex::build(
            snapshot_version,
            model_identity,
            vector_dimension,
            candidate_ids,
            packed_vectors.as_bytes(),
        )
        .map_err(index_error)?;
        Ok(Self {
            handle: SemanticUnitIndexHandle::new(index),
        })
    }

    fn snapshot_evidence(&self) -> PyResult<SemanticIndexEvidenceTuple> {
        let snapshot = self.handle.snapshot().map_err(index_error)?;
        Ok(evidence_tuple(snapshot.evidence()))
    }

    fn replace_snapshot(
        &self,
        snapshot_version: &str,
        model_identity: &str,
        vector_dimension: usize,
        candidate_ids: Vec<(String, String)>,
        packed_vectors: &Bound<'_, PyBytes>,
    ) -> PyResult<()> {
        let replacement = CoreSemanticUnitIndex::build(
            snapshot_version,
            model_identity,
            vector_dimension,
            candidate_ids,
            packed_vectors.as_bytes(),
        )
        .map_err(index_error)?;
        self.handle.replace(replacement).map_err(index_error)
    }

    fn rank_authorized(
        &self,
        py: Python<'_>,
        model_identity: String,
        query_vector: Vec<f64>,
        authorized_candidate_ids: Vec<(String, String)>,
    ) -> PyResult<SemanticIndexReportTuple> {
        let snapshot = self.handle.snapshot().map_err(index_error)?;
        py.detach(move || {
            snapshot
                .rank_authorized(&model_identity, &query_vector, &authorized_candidate_ids)
                .map(index_report_tuple)
                .map_err(index_error)
        })
    }

    fn rank_authorized_packed(
        &self,
        py: Python<'_>,
        model_identity: String,
        query_vector: Vec<f64>,
        packed_authorization: &Bound<'_, PyBytes>,
    ) -> PyResult<SemanticIndexReportTuple> {
        let snapshot = self.handle.snapshot().map_err(index_error)?;
        let packed_authorization = packed_authorization.as_bytes().to_vec();
        py.detach(move || {
            snapshot
                .rank_authorized_packed(&model_identity, &query_vector, &packed_authorization)
                .map(index_report_tuple)
                .map_err(index_error)
        })
    }

    fn preflight_authorized_packed(
        &self,
        py: Python<'_>,
        model_identity: String,
        packed_authorization: &Bound<'_, PyBytes>,
    ) -> PyResult<SemanticIndexReportTuple> {
        let snapshot = self.handle.snapshot().map_err(index_error)?;
        let packed_authorization = packed_authorization.as_bytes().to_vec();
        py.detach(move || {
            snapshot
                .preflight_authorized_packed(&model_identity, &packed_authorization)
                .map(index_report_tuple)
                .map_err(index_error)
        })
    }

    fn rank_authorized_batch_packed(
        &self,
        py: Python<'_>,
        model_identity: String,
        query_vectors: Vec<Vec<f64>>,
        packed_authorization: &Bound<'_, PyBytes>,
    ) -> PyResult<Vec<SemanticIndexReportTuple>> {
        let snapshot = self.handle.snapshot().map_err(index_error)?;
        let packed_authorization = packed_authorization.as_bytes().to_vec();
        py.detach(move || {
            snapshot
                .rank_authorized_batch_packed(
                    &model_identity,
                    &query_vectors,
                    &packed_authorization,
                )
                .map(|reports| reports.into_iter().map(index_report_tuple).collect())
                .map_err(index_error)
        })
    }
}

#[pyfunction]
fn rank_semantic_units(
    query_vector: Vec<f64>,
    candidates: Vec<(String, String, Vec<f64>)>,
) -> PyResult<SemanticUnitReportTuple> {
    let candidates: Vec<_> = candidates
        .into_iter()
        .map(
            |(item_id, unit_id, vector)| rankweave_core::SemanticUnitCandidate {
                item_id,
                unit_id,
                vector,
            },
        )
        .collect();
    let report = rankweave_core::rank_semantic_units(&query_vector, &candidates)
        .map_err(|error| PyValueError::new_err(format!("{}: {error}", error.code())))?;
    Ok((
        report.schema_version.to_owned(),
        report.algorithm_version.to_owned(),
        report.ordered_input_digest,
        report.vector_dimension,
        report
            .results
            .into_iter()
            .map(|result| (result.item_id, result.winning_unit_id, result.score))
            .collect(),
    ))
}

#[pyfunction]
fn rank_semantic_units_packed(
    query_vector: Vec<f64>,
    candidate_ids: Vec<(String, String)>,
    packed_vectors: &Bound<'_, PyBytes>,
) -> PyResult<SemanticUnitReportTuple> {
    let report = rankweave_core::rank_semantic_units_packed(
        &query_vector,
        &candidate_ids,
        packed_vectors.as_bytes(),
    )
    .map_err(|error| PyValueError::new_err(format!("{}: {error}", error.code())))?;
    Ok((
        report.schema_version.to_owned(),
        report.algorithm_version.to_owned(),
        report.ordered_input_digest,
        report.vector_dimension,
        report
            .results
            .into_iter()
            .map(|result| (result.item_id, result.winning_unit_id, result.score))
            .collect(),
    ))
}

#[pymodule]
fn _rankweave_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(theoretical_min_max_normalize, module)?)?;
    module.add_function(wrap_pyfunction!(convex_combination_score, module)?)?;
    module.add_function(wrap_pyfunction!(reciprocal_rank_fusion_score, module)?)?;
    module.add_function(wrap_pyfunction!(rank_semantic_units, module)?)?;
    module.add_function(wrap_pyfunction!(rank_semantic_units_packed, module)?)?;
    module.add_class::<SemanticUnitIndex>()?;
    Ok(())
}
