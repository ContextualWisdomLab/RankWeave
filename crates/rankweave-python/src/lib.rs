//! Python bindings for the RankWeave calculation core.

use num_bigint::BigUint;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

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
    Ok(())
}
