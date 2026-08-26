//! Python bindings for the RankWeave calculation core.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
fn theoretical_min_max_normalize(score: f64, lower: f64, upper: f64) -> f64 {
    rankweave_core::theoretical_min_max_normalize(score, lower, upper)
}

#[pyfunction]
fn reciprocal_rank_fusion_score(ranks: Vec<u64>, rank_constant_eta: u64) -> f64 {
    rankweave_core::reciprocal_rank_fusion_score(&ranks, rank_constant_eta)
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

#[pymodule]
fn _rankweave_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(theoretical_min_max_normalize, module)?)?;
    module.add_function(wrap_pyfunction!(reciprocal_rank_fusion_score, module)?)?;
    module.add_function(wrap_pyfunction!(rank_semantic_units, module)?)?;
    Ok(())
}
