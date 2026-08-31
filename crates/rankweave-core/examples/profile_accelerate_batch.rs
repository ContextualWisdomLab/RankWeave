//! Measure Accelerate f64 matrix-matrix parity at the consumer workload shape.

#[cfg(target_os = "macos")]
mod macos {
    use std::time::Instant;

    const CANDIDATES: usize = 6_578;
    const DIMENSION: usize = 3_072;
    const QUERIES: usize = 4;
    const CBLAS_ROW_MAJOR: i32 = 101;
    const CBLAS_NO_TRANS: i32 = 111;

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
        let mut elapsed = Vec::new();
        for _ in 0..30 {
            let started = Instant::now();
            multiply(&matrix, &queries_by_coordinate, &mut accelerate);
            elapsed.push(started.elapsed().as_secs_f64() * 1_000.0);
        }
        elapsed.sort_by(f64::total_cmp);
        let mean = elapsed.iter().sum::<f64>() / elapsed.len() as f64;
        println!(
            "shape={CANDIDATES}x{DIMENSION}x{QUERIES} min_ms={:.3} mean_ms={mean:.3} p95_ms={:.3} max_ms={:.3} bit_mismatches={mismatched} top4_mismatches={top_four_mismatches} max_abs_diff={maximum_absolute_difference:e}",
            elapsed[0], elapsed[27], elapsed[29]
        );
    }
}

fn main() {
    #[cfg(target_os = "macos")]
    macos::run();
    #[cfg(not(target_os = "macos"))]
    eprintln!("Accelerate profile is available only on macOS");
}
