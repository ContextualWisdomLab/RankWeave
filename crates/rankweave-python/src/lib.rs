//! Python bindings for the RankWeave calculation core.

use pyo3::prelude::*;

#[pyfunction]
fn theoretical_min_max_normalize(score: f64, lower: f64, upper: f64) -> f64 {
    rankweave_core::theoretical_min_max_normalize(score, lower, upper)
}

#[pyfunction]
fn reciprocal_rank_fusion_score(ranks: Vec<u64>, rank_constant_eta: u64) -> f64 {
    rankweave_core::reciprocal_rank_fusion_score(&ranks, rank_constant_eta)
}

#[pymodule]
fn _rankweave_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(theoretical_min_max_normalize, module)?)?;
    module.add_function(wrap_pyfunction!(reciprocal_rank_fusion_score, module)?)?;
    Ok(())
}
