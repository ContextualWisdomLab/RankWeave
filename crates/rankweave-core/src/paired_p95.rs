//! Paired empirical p95 comparison under an explicit whole-unit resampling plan.

use std::collections::HashMap;

use sha2::{Digest, Sha256};

use super::update_length_prefixed;

/// Calculation evidence, not certification of a sampling design or coverage.
#[derive(Debug)]
pub struct PairedP95Report {
    /// Version of the result envelope.
    pub schema_version: &'static str,
    /// Exact empirical-quantile and replay calculation contract.
    pub algorithm_version: &'static str,
    /// Integrity binding of observations, partition, draws, and allocation bound.
    pub ordered_input_digest: String,
    /// Number of paired observations, including all supplied terminal outcomes.
    pub observation_count: usize,
    /// Number of caller-declared sampling units, not certified independent units.
    pub resampling_unit_count: usize,
    /// Baseline inverse-empirical-CDF quantile at 19/20.
    pub baseline_p95: f64,
    /// Candidate inverse-empirical-CDF quantile at 19/20.
    pub candidate_p95: f64,
    /// Candidate p95 minus baseline p95.
    pub p95_difference: f64,
    /// Empirical 1/40 quantile of the replayed differences.
    pub interval_low: f64,
    /// Empirical 39/40 quantile of the replayed differences.
    pub interval_high: f64,
    /// Differences retained in caller-supplied resample order.
    pub resampled_differences: Vec<f64>,
    /// Expanded row counts; unequal unit sizes need not preserve sample size.
    pub resample_observation_counts: Vec<usize>,
}

fn empirical_quantile(sorted_values: &[f64], numerator: u128, denominator: u128) -> f64 {
    let rank = (sorted_values.len() as u128 * numerator).div_ceil(denominator);
    sorted_values[rank as usize - 1]
}

fn paired_p95(
    baseline_values: &mut [f64],
    candidate_values: &mut [f64],
) -> Result<(f64, f64, f64), &'static str> {
    baseline_values.sort_by(f64::total_cmp);
    candidate_values.sort_by(f64::total_cmp);
    let baseline_p95 = empirical_quantile(baseline_values, 19, 20);
    let candidate_p95 = empirical_quantile(candidate_values, 19, 20);
    let difference = candidate_p95 - baseline_p95;
    if !difference.is_finite() {
        return Err("p95 difference must be finite");
    }
    Ok((baseline_p95, candidate_p95, difference))
}

/// Replay complete paired units and compare each policy's p95 separately.
///
/// Each observation is `(opaque_id, baseline_value, candidate_value)`. Units
/// must partition those IDs exactly once. Each draw lists zero-based unit
/// indices with replacement and must contain exactly the original unit count.
/// Every occurrence expands the entire unit identically for both policies.
/// The caller owns the design, draw generation, units, and interpretation.
/// Values are generic finite scalars; no missing outcome is imputed or dropped.
///
/// # Errors
/// Rejects empty/duplicate IDs, non-finite values, incomplete/overlapping units,
/// malformed draws, resamples exceeding the explicit row bound, and overflow
/// in a p95 difference. The row bound is checked before each replay allocation.
pub fn compare_paired_p95(
    observation_pairs: &[(String, f64, f64)],
    resampling_units: &[Vec<String>],
    unit_draws: &[Vec<usize>],
    max_resample_observations: usize,
) -> Result<PairedP95Report, &'static str> {
    if observation_pairs.is_empty() {
        return Err("observation_pairs must not be empty");
    }
    let mut row_by_id = HashMap::new();
    let mut hasher = Sha256::new();
    hasher.update(b"rankweave.paired-p95.request.v1\0");
    hasher.update((observation_pairs.len() as u64).to_be_bytes());
    for (row_index, (observation_id, baseline_value, candidate_value)) in
        observation_pairs.iter().enumerate()
    {
        if observation_id.is_empty()
            || row_by_id
                .insert(observation_id.as_str(), row_index)
                .is_some()
        {
            return Err("observation identifiers must be non-empty and unique");
        }
        if !baseline_value.is_finite() || !candidate_value.is_finite() {
            return Err("paired observations must be finite");
        }
        update_length_prefixed(&mut hasher, observation_id.as_bytes());
        hasher.update(baseline_value.to_be_bytes());
        hasher.update(candidate_value.to_be_bytes());
    }
    let mut seen_rows = vec![false; observation_pairs.len()];
    let mut unit_rows = Vec::with_capacity(resampling_units.len());
    hasher.update((resampling_units.len() as u64).to_be_bytes());
    for unit_members in resampling_units {
        if unit_members.is_empty() {
            return Err("resampling units must not be empty");
        }
        let mut member_rows = Vec::with_capacity(unit_members.len());
        hasher.update((unit_members.len() as u64).to_be_bytes());
        for observation_id in unit_members {
            let row_index = *row_by_id
                .get(observation_id.as_str())
                .ok_or("resampling unit contains an unknown observation")?;
            if seen_rows[row_index] {
                return Err("resampling units must not overlap");
            }
            seen_rows[row_index] = true;
            member_rows.push(row_index);
            update_length_prefixed(&mut hasher, observation_id.as_bytes());
        }
        unit_rows.push(member_rows);
    }
    if seen_rows.iter().any(|seen| !seen) {
        return Err("resampling units must cover every observation");
    }
    if unit_draws.is_empty() {
        return Err("unit_draws must not be empty");
    }
    hasher.update((max_resample_observations as u64).to_be_bytes());
    hasher.update((unit_draws.len() as u64).to_be_bytes());
    let mut resample_observation_counts = Vec::with_capacity(unit_draws.len());
    for unit_draw in unit_draws {
        if unit_draw.len() != unit_rows.len() {
            return Err("each draw must contain the original number of units");
        }
        let mut row_count = 0;
        for &unit_index in unit_draw {
            let member_rows = unit_rows
                .get(unit_index)
                .ok_or("draw contains an unknown unit")?;
            if member_rows.len() > max_resample_observations - row_count {
                return Err("resample exceeds max_resample_observations");
            }
            row_count += member_rows.len();
            hasher.update((unit_index as u64).to_be_bytes());
        }
        resample_observation_counts.push(row_count);
    }
    let mut baseline_values: Vec<_> = observation_pairs.iter().map(|row| row.1).collect();
    let mut candidate_values: Vec<_> = observation_pairs.iter().map(|row| row.2).collect();
    let (baseline_p95, candidate_p95, p95_difference) =
        paired_p95(&mut baseline_values, &mut candidate_values)?;
    let mut resampled_differences = Vec::with_capacity(unit_draws.len());
    for (unit_draw, &row_count) in unit_draws.iter().zip(&resample_observation_counts) {
        let mut baseline_values = Vec::with_capacity(row_count);
        let mut candidate_values = Vec::with_capacity(row_count);
        for &unit_index in unit_draw {
            for &row_index in &unit_rows[unit_index] {
                baseline_values.push(observation_pairs[row_index].1);
                candidate_values.push(observation_pairs[row_index].2);
            }
        }
        resampled_differences.push(paired_p95(&mut baseline_values, &mut candidate_values)?.2);
    }
    let mut sorted_differences = resampled_differences.clone();
    sorted_differences.sort_by(f64::total_cmp);
    Ok(PairedP95Report {
        schema_version: "rankweave.paired-p95.v1",
        algorithm_version: "rankweave.paired-p95.hf1-unit-replay.v1",
        ordered_input_digest: format!("sha256:{:x}", hasher.finalize()),
        observation_count: observation_pairs.len(),
        resampling_unit_count: unit_rows.len(),
        baseline_p95,
        candidate_p95,
        p95_difference,
        interval_low: empirical_quantile(&sorted_differences, 1, 40),
        interval_high: empirical_quantile(&sorted_differences, 39, 40),
        resampled_differences,
        resample_observation_counts,
    })
}

#[cfg(test)]
mod tests {
    use super::compare_paired_p95;

    #[test]
    fn whole_unit_replay_preserves_pairs_counts_and_request_identity() {
        let observations = vec![
            ("a".into(), 1.0, 100.0),
            ("b".into(), 100.0, 1.0),
            ("c".into(), 2.0, 2.0),
        ];
        let units = vec![vec!["a".into(), "c".into()], vec!["b".into()]];
        let draws = vec![vec![0, 0], vec![1, 1], vec![0, 1]];
        let report = compare_paired_p95(&observations, &units, &draws, 4).unwrap();
        assert_eq!(
            (
                report.baseline_p95,
                report.candidate_p95,
                report.p95_difference
            ),
            (100.0, 100.0, 0.0)
        );
        assert_eq!(report.resampled_differences, vec![98.0, -99.0, 0.0]);
        assert_eq!(report.resample_observation_counts, vec![4, 2, 3]);
        assert_eq!((report.interval_low, report.interval_high), (-99.0, 98.0));
        assert_eq!(
            (report.observation_count, report.resampling_unit_count),
            (3, 2)
        );
        assert_eq!(report.schema_version, "rankweave.paired-p95.v1");
        assert_eq!(
            report.algorithm_version,
            "rankweave.paired-p95.hf1-unit-replay.v1"
        );
        assert!(format!("{report:?}").contains("resampled_differences"));
        let digest = report.ordered_input_digest;
        assert!(digest.starts_with("sha256:"));
        assert_eq!(
            digest,
            compare_paired_p95(&observations, &units, &draws, 4)
                .unwrap()
                .ordered_input_digest
        );
        let mut reversed_draws = draws.clone();
        reversed_draws.reverse();
        let mut changed_observations = observations.clone();
        changed_observations[0].2 = 99.0;
        let changed_units = vec![vec!["c".into(), "a".into()], vec!["b".into()]];
        for changed_digest in [
            compare_paired_p95(&observations, &units, &reversed_draws, 4)
                .unwrap()
                .ordered_input_digest,
            compare_paired_p95(&changed_observations, &units, &draws, 4)
                .unwrap()
                .ordered_input_digest,
            compare_paired_p95(&observations, &changed_units, &draws, 4)
                .unwrap()
                .ordered_input_digest,
            compare_paired_p95(&observations, &units, &draws, 5)
                .unwrap()
                .ordered_input_digest,
        ] {
            assert_ne!(digest, changed_digest);
        }
    }

    #[test]
    fn empirical_quantiles_use_integer_ranks_without_interpolation() {
        let observations: Vec<_> = (1..=40)
            .map(|value| (value.to_string(), f64::from(value), f64::from(value * 2)))
            .collect();
        let units: Vec<_> = (1..=40).map(|value| vec![value.to_string()]).collect();
        let draws: Vec<_> = (0..40).map(|index| vec![index; 40]).collect();
        let report = compare_paired_p95(&observations, &units, &draws, 40).unwrap();
        assert_eq!(
            (
                report.baseline_p95,
                report.candidate_p95,
                report.p95_difference
            ),
            (38.0, 76.0, 38.0)
        );
        assert_eq!((report.interval_low, report.interval_high), (1.0, 39.0));
        assert_eq!(
            report.resampled_differences,
            (1..=40).map(f64::from).collect::<Vec<_>>()
        );
    }

    #[test]
    fn invalid_observations_partitions_draws_and_expansion_fail_closed() {
        let observations = vec![("a".into(), 1.0, 2.0), ("b".into(), 2.0, 3.0)];
        let units = vec![vec!["a".into()], vec!["b".into()]];
        let draws = vec![vec![0, 1]];
        assert_eq!(
            compare_paired_p95(&[], &units, &draws, 2).err(),
            Some("observation_pairs must not be empty")
        );
        for invalid_id in ["", "a"] {
            let mut changed = observations.clone();
            changed[1].0 = invalid_id.into();
            assert_eq!(
                compare_paired_p95(&changed, &units, &draws, 2).err(),
                Some("observation identifiers must be non-empty and unique")
            );
        }
        for (baseline_value, candidate_value) in [
            (f64::NAN, 1.0),
            (1.0, f64::NAN),
            (f64::INFINITY, 1.0),
            (1.0, f64::NEG_INFINITY),
        ] {
            let mut changed = observations.clone();
            changed[0].1 = baseline_value;
            changed[0].2 = candidate_value;
            assert_eq!(
                compare_paired_p95(&changed, &units, &draws, 2).err(),
                Some("paired observations must be finite")
            );
        }
        for (changed_units, message) in [
            (vec![], "resampling units must cover every observation"),
            (vec![vec![]], "resampling units must not be empty"),
            (
                vec![vec!["missing".into()]],
                "resampling unit contains an unknown observation",
            ),
            (
                vec![vec!["a".into(), "a".into()]],
                "resampling units must not overlap",
            ),
            (
                vec![vec!["a".into()], vec!["a".into(), "b".into()]],
                "resampling units must not overlap",
            ),
            (
                vec![vec!["a".into()]],
                "resampling units must cover every observation",
            ),
        ] {
            assert_eq!(
                compare_paired_p95(&observations, &changed_units, &draws, 2).err(),
                Some(message)
            );
        }
        for (changed_draws, message) in [
            (vec![], "unit_draws must not be empty"),
            (
                vec![vec![0]],
                "each draw must contain the original number of units",
            ),
            (vec![vec![0, usize::MAX]], "draw contains an unknown unit"),
        ] {
            assert_eq!(
                compare_paired_p95(&observations, &units, &changed_draws, 2).err(),
                Some(message)
            );
        }
        for row_bound in [0, 1] {
            assert_eq!(
                compare_paired_p95(&observations, &units, &draws, row_bound).err(),
                Some("resample exceeds max_resample_observations")
            );
        }
        let mut overflow = observations.clone();
        overflow[0].1 = -f64::MAX;
        overflow[0].2 = f64::MAX;
        overflow[1].1 = -f64::MAX;
        assert_eq!(
            compare_paired_p95(&overflow, &units, &draws, 2).err(),
            Some("p95 difference must be finite")
        );
        overflow[1].1 = f64::MAX;
        overflow[1].2 = f64::MAX;
        assert_eq!(
            compare_paired_p95(&overflow, &units, &[vec![0, 0]], 2).err(),
            Some("p95 difference must be finite")
        );
    }
}
