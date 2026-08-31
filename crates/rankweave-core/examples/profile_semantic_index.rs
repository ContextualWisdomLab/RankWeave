//! Profile exact snapshot build and authorized ranking with synthetic vectors.

use std::env;
use std::time::Instant;

use rankweave_core::semantic_index::SemanticUnitIndex;

fn positive_usize(value: Option<String>, label: &str) -> usize {
    let parsed = value
        .unwrap_or_else(|| panic!("missing {label}"))
        .parse::<usize>()
        .unwrap_or_else(|_| panic!("invalid {label}"));
    assert!(parsed > 0, "{label} must be positive");
    parsed
}

fn main() {
    let mut arguments = env::args().skip(1);
    let candidate_count = positive_usize(arguments.next(), "candidate count");
    let vector_dimension = positive_usize(arguments.next(), "vector dimension");
    let item_count = positive_usize(arguments.next(), "item count");
    assert!(
        item_count <= candidate_count,
        "item count exceeds candidates"
    );
    assert!(arguments.next().is_none(), "unexpected argument");

    let mut one_vector = Vec::with_capacity(vector_dimension * size_of::<f64>());
    one_vector.extend_from_slice(&1.0_f64.to_be_bytes());
    one_vector.resize(vector_dimension * size_of::<f64>(), 0);
    let packed_vectors = one_vector.repeat(candidate_count);
    let candidate_ids = (0..candidate_count)
        .map(|index| {
            (
                format!("item-{:08}", index % item_count),
                format!("unit-{index:08}"),
            )
        })
        .collect::<Vec<_>>();
    let query_vector = std::iter::once(1.0)
        .chain(std::iter::repeat_n(0.0, vector_dimension - 1))
        .collect::<Vec<_>>();

    let build_started = Instant::now();
    let index = SemanticUnitIndex::build(
        "synthetic-snapshot-v1",
        "synthetic-model-v1",
        vector_dimension,
        candidate_ids.clone(),
        &packed_vectors,
    )
    .expect("synthetic snapshot must build");
    let build_elapsed = build_started.elapsed();

    let rank_started = Instant::now();
    let report = index
        .rank_authorized("synthetic-model-v1", &query_vector, &candidate_ids)
        .expect("synthetic authorization must rank");
    let rank_elapsed = rank_started.elapsed();

    println!(
        "candidates={candidate_count} dimension={vector_dimension} items={item_count} bytes={} build_ms={:.3} rank_ms={:.3} workers={} results={} input_digest={} output_digest={}",
        packed_vectors.len(),
        build_elapsed.as_secs_f64() * 1_000.0,
        rank_elapsed.as_secs_f64() * 1_000.0,
        report.worker_count,
        report.results.len(),
        report.ordered_input_digest,
        report.output_digest,
    );
}
