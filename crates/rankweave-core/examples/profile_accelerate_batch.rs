//! Measure Accelerate f64 matrix-matrix parity at the consumer workload shape.

#[cfg(target_os = "macos")]
mod macos {
    use std::time::Instant;

    const CANDIDATES: usize = 6_578;
    const DIMENSION: usize = 3_072;
    const QUERIES: usize = 4;
    const CBLAS_ROW_MAJOR: i32 = 101;
    const CBLAS_NO_TRANS: i32 = 111;

    fn gamma(term_count: usize) -> f64 {
        let unit_roundoff = 2.0_f64.powi(-53);
        let product = term_count as f64 * unit_roundoff;
        product / (1.0 - product)
    }

    fn norm(values: impl Iterator<Item = f64>) -> f64 {
        values.map(|value| value * value).sum::<f64>().sqrt()
    }

    fn ambiguity_set(intervals: &[(f64, f64)], limit: usize) -> Vec<usize> {
        let mut lower_bounds = intervals
            .iter()
            .enumerate()
            .map(|(index, interval)| (interval.0, index))
            .collect::<Vec<_>>();
        lower_bounds.sort_by(|left, right| {
            right
                .0
                .total_cmp(&left.0)
                .then_with(|| left.1.cmp(&right.1))
        });
        let kth_lower = lower_bounds[limit - 1].0;
        intervals
            .iter()
            .enumerate()
            .filter_map(|(index, interval)| (interval.1 >= kth_lower).then_some(index))
            .collect()
    }

    #[link(name = "Accelerate", kind = "framework")]
    unsafe extern "C" {
        fn cblas_dgemm(
            order: i32,
            transpose_a: i32,
            transpose_b: i32,
            rows_a: i32,
            columns_b: i32,
            shared_dimension: i32,
            alpha: f64,
            a: *const f64,
            leading_a: i32,
            b: *const f64,
            leading_b: i32,
            beta: f64,
            c: *mut f64,
            leading_c: i32,
        );
    }

    fn value(row: usize, column: usize) -> f64 {
        let residue = (row.wrapping_mul(131) + column.wrapping_mul(17)) % 1_009;
        (residue as f64 - 504.0) / 509.0
    }

    fn multiply(matrix: &[f64], queries_by_coordinate: &[f64], output: &mut [f64]) {
        // SAFETY: all pointers reference contiguous f64 buffers whose exact
        // row-major extents and leading dimensions are supplied below.
        unsafe {
            cblas_dgemm(
                CBLAS_ROW_MAJOR,
                CBLAS_NO_TRANS,
                CBLAS_NO_TRANS,
                CANDIDATES as i32,
                QUERIES as i32,
                DIMENSION as i32,
                1.0,
                matrix.as_ptr(),
                DIMENSION as i32,
                queries_by_coordinate.as_ptr(),
                QUERIES as i32,
                0.0,
                output.as_mut_ptr(),
                QUERIES as i32,
            );
        }
    }

    fn top_four(scores: &[f64], query: usize) -> [usize; 4] {
        let mut candidates = (0..CANDIDATES).collect::<Vec<_>>();
        candidates.sort_by(|left, right| {
            scores[right * QUERIES + query]
                .total_cmp(&scores[left * QUERIES + query])
                .then_with(|| left.cmp(right))
        });
        candidates[..4].try_into().expect("four ranked candidates")
    }

    fn screened_top_four(
        matrix: &[f64],
        queries_by_coordinate: &[f64],
        approximate_dots: &[f64],
        candidate_norms: &[f64],
        query_norms: &[f64],
        query: usize,
    ) -> ([usize; 4], usize) {
        // Higham's dot-product model bounds each BLAS result and the
        // coordinate-ordered scalar reference by gamma_n * |x|^T|y|.
        // Cauchy-Schwarz gives |x|^T|y| <= ||x|| ||y||, so the scalar
        // cosine lies within 2*gamma_n of the BLAS cosine. Equality remains
        // ambiguous; only a strict upper-bound exclusion is safe.
        let error = 2.0 * gamma(DIMENSION);
        let intervals = (0..CANDIDATES)
            .map(|candidate| {
                let approximate = approximate_dots[candidate * QUERIES + query]
                    / (candidate_norms[candidate] * query_norms[query]);
                (
                    (approximate - error).max(-1.0),
                    (approximate + error).min(1.0),
                )
            })
            .collect::<Vec<_>>();
        let ambiguous = ambiguity_set(&intervals, 4);
        let mut exact = ambiguous
            .iter()
            .map(|candidate| {
                let dot = (0..DIMENSION).fold(0.0, |sum, coordinate| {
                    sum + matrix[candidate * DIMENSION + coordinate]
                        * queries_by_coordinate[coordinate * QUERIES + query]
                });
                (
                    dot / (candidate_norms[*candidate] * query_norms[query]),
                    *candidate,
                )
            })
            .collect::<Vec<_>>();
        exact.sort_by(|left, right| {
            right
                .0
                .total_cmp(&left.0)
                .then_with(|| left.1.cmp(&right.1))
        });
        (
            exact[..4]
                .iter()
                .map(|entry| entry.1)
                .collect::<Vec<_>>()
                .try_into()
                .expect("four exact ambiguous candidates"),
            ambiguous.len(),
        )
    }

    pub fn run() {
        let matrix = (0..CANDIDATES)
            .flat_map(|row| (0..DIMENSION).map(move |column| value(row, column)))
            .collect::<Vec<_>>();
        let queries_by_coordinate = (0..DIMENSION)
            .flat_map(|coordinate| {
                (0..QUERIES).map(move |query| value(CANDIDATES + query, coordinate))
            })
            .collect::<Vec<_>>();
        let mut accelerate = vec![0.0; CANDIDATES * QUERIES];
        multiply(&matrix, &queries_by_coordinate, &mut accelerate);
        let candidate_norms = (0..CANDIDATES)
            .map(|candidate| {
                norm(
                    matrix[candidate * DIMENSION..(candidate + 1) * DIMENSION]
                        .iter()
                        .copied(),
                )
            })
            .collect::<Vec<_>>();
        let query_norms = (0..QUERIES)
            .map(|query| {
                norm(
                    (0..DIMENSION)
                        .map(|coordinate| queries_by_coordinate[coordinate * QUERIES + query]),
                )
            })
            .collect::<Vec<_>>();
        let mut scalar = vec![0.0; CANDIDATES * QUERIES];
        for candidate in 0..CANDIDATES {
            for coordinate in 0..DIMENSION {
                let candidate_value = matrix[candidate * DIMENSION + coordinate];
                for query in 0..QUERIES {
                    scalar[candidate * QUERIES + query] +=
                        candidate_value * queries_by_coordinate[coordinate * QUERIES + query];
                }
            }
        }
        let mismatched = scalar
            .iter()
            .zip(&accelerate)
            .filter(|(left, right)| left.to_bits() != right.to_bits())
            .count();
        let maximum_absolute_difference = scalar
            .iter()
            .zip(&accelerate)
            .map(|(left, right)| (left - right).abs())
            .fold(0.0, f64::max);
        let top_four_mismatches = (0..QUERIES)
            .filter(|query| top_four(&scalar, *query) != top_four(&accelerate, *query))
            .count();
        let screened = (0..QUERIES)
            .map(|query| {
                screened_top_four(
                    &matrix,
                    &queries_by_coordinate,
                    &accelerate,
                    &candidate_norms,
                    &query_norms,
                    query,
                )
            })
            .collect::<Vec<_>>();
        let screened_top_four_mismatches = screened
            .iter()
            .enumerate()
            .filter(|(query, result)| top_four(&scalar, *query) != result.0)
            .count();
        let maximum_ambiguity = screened
            .iter()
            .map(|result| result.1)
            .max()
            .expect("queries are nonempty");
        let mut elapsed = Vec::new();
        for _ in 0..30 {
            let started = Instant::now();
            multiply(&matrix, &queries_by_coordinate, &mut accelerate);
            for query in 0..QUERIES {
                let _ = screened_top_four(
                    &matrix,
                    &queries_by_coordinate,
                    &accelerate,
                    &candidate_norms,
                    &query_norms,
                    query,
                );
            }
            elapsed.push(started.elapsed().as_secs_f64() * 1_000.0);
        }
        elapsed.sort_by(f64::total_cmp);
        let mean = elapsed.iter().sum::<f64>() / elapsed.len() as f64;
        println!(
            "shape={CANDIDATES}x{DIMENSION}x{QUERIES} min_ms={:.3} mean_ms={mean:.3} p95_ms={:.3} max_ms={:.3} bit_mismatches={mismatched} approximate_top4_mismatches={top_four_mismatches} screened_top4_mismatches={screened_top_four_mismatches} maximum_ambiguity={maximum_ambiguity} max_abs_diff={maximum_absolute_difference:e}",
            elapsed[0], elapsed[27], elapsed[29]
        );
    }

    #[test]
    fn equal_intervals_force_complete_scalar_fallback() {
        let intervals = vec![(0.5, 0.5); 8];
        assert_eq!(ambiguity_set(&intervals, 4), (0..8).collect::<Vec<_>>());
    }

    #[test]
    fn near_tie_interval_is_never_excluded() {
        let intervals = vec![(0.9, 0.91), (0.89, 0.905), (0.1, 0.2)];
        assert_eq!(ambiguity_set(&intervals, 1), vec![0, 1]);
    }
}

fn main() {
    #[cfg(target_os = "macos")]
    macos::run();
    #[cfg(not(target_os = "macos"))]
    eprintln!("Accelerate profile is available only on macOS");
}
