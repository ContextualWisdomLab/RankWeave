"""Time-respecting backtesting for fixed convex retrieval-fusion policies."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.evaluation import RankingEvaluationReport, evaluate_rankings
from rankweave.ranked_list_fusion import weighted_convex_fuse
from rankweave.tuning import (
    MEAN_NDCG_OBJECTIVE,
    WeightedConvexTuningReport,
    tune_weighted_convex_fusion,
)

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
PolicyIdentifier = TypeVar("PolicyIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)
WindowIdentifier = TypeVar("WindowIdentifier", bound=Hashable)


@dataclass(frozen=True)
class WeightedConvexBacktestWindowDefinition(
    Generic[WindowIdentifier, QueryIdentifier]
):
    """One explicit training and held-out query window in assessment order."""

    window_id: WindowIdentifier
    training_query_ids: tuple[QueryIdentifier, ...]
    held_out_query_ids: tuple[QueryIdentifier, ...]

    def __post_init__(self) -> None:
        """Snapshot caller-provided query sequences as immutable tuples."""
        object.__setattr__(
            self,
            "training_query_ids",
            tuple(self.training_query_ids),
        )
        object.__setattr__(
            self,
            "held_out_query_ids",
            tuple(self.held_out_query_ids),
        )


@dataclass(frozen=True)
class WeightedConvexBacktestWindow(
    Generic[
        WindowIdentifier,
        PolicyIdentifier,
        QueryIdentifier,
        ItemIdentifier,
    ]
):
    """One fitted training window and its immutable future-query evidence."""

    window_id: WindowIdentifier
    training_query_ids: tuple[QueryIdentifier, ...]
    held_out_query_ids: tuple[QueryIdentifier, ...]
    training_available_time_max: datetime
    held_out_available_time_min: datetime
    held_out_available_time_max: datetime
    tuning: WeightedConvexTuningReport[PolicyIdentifier, QueryIdentifier]
    held_out_rankings: tuple[
        tuple[QueryIdentifier, tuple[ItemIdentifier, ...]], ...
    ]
    held_out_evaluation: RankingEvaluationReport[QueryIdentifier]


@dataclass(frozen=True)
class WeightedConvexBacktestReport(
    Generic[
        WindowIdentifier,
        PolicyIdentifier,
        QueryIdentifier,
        ItemIdentifier,
    ]
):
    """All temporal windows, out-of-sample evidence, and final policy advice."""

    cutoff: int
    objective_name: str
    initial_training_query_ids: tuple[QueryIdentifier, ...]
    windows: tuple[
        WeightedConvexBacktestWindow[
            WindowIdentifier,
            PolicyIdentifier,
            QueryIdentifier,
            ItemIdentifier,
        ],
        ...,
    ]
    out_of_sample_rankings: tuple[
        tuple[QueryIdentifier, tuple[ItemIdentifier, ...]], ...
    ]
    out_of_sample_evaluation: RankingEvaluationReport[QueryIdentifier]
    final_tuning: WeightedConvexTuningReport[
        PolicyIdentifier, QueryIdentifier
    ]


def _normalize_available_times(
    query_ids: tuple[QueryIdentifier, ...],
    available_time_by_query: Mapping[QueryIdentifier, datetime],
) -> dict[QueryIdentifier, datetime]:
    """Validate complete timezone-aware availability and normalize it to UTC."""
    query_id_set = set(query_ids)
    available_query_ids = set(available_time_by_query)
    if available_query_ids != query_id_set:
        missing = sorted(query_id_set - available_query_ids, key=repr)
        extra = sorted(available_query_ids - query_id_set, key=repr)
        raise ValueError(
            "result and availability query sets must match; "
            f"missing availability={missing!r}, "
            f"extra availability={extra!r}"
        )

    normalized: dict[QueryIdentifier, datetime] = {}
    for query_id in query_ids:
        available_time = available_time_by_query[query_id]
        if not isinstance(available_time, datetime):
            raise ValueError(
                f"availability for query {query_id!r} must be a datetime"
            )
        if available_time.tzinfo is None or available_time.utcoffset() is None:
            raise ValueError(
                f"availability for query {query_id!r} must be timezone-aware"
            )
        normalized[query_id] = available_time.astimezone(timezone.utc)
    return normalized


def _snapshot_unique_query_ids(
    query_ids: Sequence[QueryIdentifier],
    *,
    label: str,
    window_id: WindowIdentifier,
) -> tuple[QueryIdentifier, ...]:
    """Snapshot one non-empty sequence of unique, hashable query identifiers."""
    snapshot = tuple(query_ids)
    if not snapshot:
        raise ValueError(
            f"window {window_id!r} requires non-empty {label} query IDs"
        )
    seen: set[QueryIdentifier] = set()
    for query_id in snapshot:
        try:
            if query_id in seen:
                raise ValueError(
                    f"window {window_id!r} contains duplicate {label} "
                    f"query {query_id!r}"
                )
            seen.add(query_id)
        except TypeError as exc:
            raise ValueError(
                f"window {window_id!r} {label} query identifier "
                "must be hashable"
            ) from exc
    return snapshot


def _validate_window_structure(
    windows: Sequence[
        WeightedConvexBacktestWindowDefinition[
            WindowIdentifier, QueryIdentifier
        ]
    ],
    query_ids: tuple[QueryIdentifier, ...],
) -> tuple[
    tuple[
        WeightedConvexBacktestWindowDefinition[
            WindowIdentifier, QueryIdentifier
        ],
        ...,
    ],
    tuple[QueryIdentifier, ...],
]:
    """Validate identifiers, complete query accounting, and held-out uniqueness."""
    window_snapshot = tuple(windows)
    if not window_snapshot:
        raise ValueError("backtesting requires at least one assessment window")

    query_universe = set(query_ids)
    validated_windows = []
    seen_window_ids: set[WindowIdentifier] = set()
    seen_held_out: set[QueryIdentifier] = set()

    for window in window_snapshot:
        if not isinstance(window, WeightedConvexBacktestWindowDefinition):
            raise ValueError(
                "windows must contain WeightedConvexBacktestWindowDefinition "
                "records"
            )
        try:
            if window.window_id in seen_window_ids:
                raise ValueError(
                    f"duplicate window identifier {window.window_id!r}"
                )
            seen_window_ids.add(window.window_id)
        except TypeError as exc:
            raise ValueError("window identifier must be hashable") from exc

        training_query_ids = _snapshot_unique_query_ids(
            window.training_query_ids,
            label="training",
            window_id=window.window_id,
        )
        held_out_query_ids = _snapshot_unique_query_ids(
            window.held_out_query_ids,
            label="held-out",
            window_id=window.window_id,
        )
        unknown = (
            set(training_query_ids) | set(held_out_query_ids)
        ) - query_universe
        if unknown:
            raise ValueError(
                f"window {window.window_id!r} contains unknown query "
                f"identifiers: {sorted(unknown, key=repr)!r}"
            )
        overlap = set(training_query_ids) & set(held_out_query_ids)
        if overlap:
            raise ValueError(
                f"window {window.window_id!r} training and held-out queries "
                f"overlap: {sorted(overlap, key=repr)!r}"
            )
        repeated = set(held_out_query_ids) & seen_held_out
        if repeated:
            raise ValueError(
                f"queries are held out more than once: "
                f"{sorted(repeated, key=repr)!r}"
            )
        seen_held_out.update(held_out_query_ids)
        validated_windows.append(
            WeightedConvexBacktestWindowDefinition(
                window_id=window.window_id,
                training_query_ids=training_query_ids,
                held_out_query_ids=held_out_query_ids,
            )
        )

    initial_training_query_ids = validated_windows[0].training_query_ids
    initial_training_set = set(initial_training_query_ids)
    initial_reused_as_held_out = initial_training_set & seen_held_out
    if initial_reused_as_held_out:
        raise ValueError(
            "initial training queries may not be held out later: "
            f"{sorted(initial_reused_as_held_out, key=repr)!r}"
        )
    missing_from_accounting = query_universe - (
        initial_training_set | seen_held_out
    )
    if missing_from_accounting:
        raise ValueError(
            "queries are neither initial training nor held out exactly once: "
            f"{sorted(missing_from_accounting, key=repr)!r}"
        )

    return tuple(validated_windows), initial_training_query_ids


def _validate_temporal_order(
    windows: tuple[
        WeightedConvexBacktestWindowDefinition[
            WindowIdentifier, QueryIdentifier
        ],
        ...,
    ],
    available_times: Mapping[QueryIdentifier, datetime],
) -> tuple[tuple[datetime, datetime, datetime], ...]:
    """Return per-window UTC bounds after enforcing forward-only assessment."""
    bounds = []
    previous_held_out_max: datetime | None = None
    for window in windows:
        training_max = max(
            available_times[query_id]
            for query_id in window.training_query_ids
        )
        held_out_times = tuple(
            available_times[query_id]
            for query_id in window.held_out_query_ids
        )
        held_out_min = min(held_out_times)
        held_out_max = max(held_out_times)
        if (
            previous_held_out_max is not None
            and previous_held_out_max >= held_out_min
        ):
            raise ValueError(
                "held-out time ranges must be ordered and non-overlapping"
            )
        if training_max >= held_out_min:
            raise ValueError(
                f"window {window.window_id!r} training evidence must precede "
                "every held-out query"
            )
        bounds.append((training_max, held_out_min, held_out_max))
        previous_held_out_max = held_out_max
    return tuple(bounds)


def backtest_weighted_convex_fusion(
    channel_results_by_query: Mapping[
        QueryIdentifier,
        Mapping[str, Sequence[tuple[ItemIdentifier, float]]],
    ],
    relevance_by_query: Mapping[
        QueryIdentifier, Mapping[ItemIdentifier, float]
    ],
    candidate_channel_weights: Mapping[
        PolicyIdentifier, Mapping[str, float]
    ],
    available_time_by_query: Mapping[QueryIdentifier, datetime],
    windows: Sequence[
        WeightedConvexBacktestWindowDefinition[
            WindowIdentifier, QueryIdentifier
        ]
    ],
    *,
    cutoff: int,
    objective_name: str = MEAN_NDCG_OBJECTIVE,
) -> WeightedConvexBacktestReport[
    WindowIdentifier,
    PolicyIdentifier,
    QueryIdentifier,
    ItemIdentifier,
]:
    """Backtest fixed convex fusion policies without future evidence leakage.

    The caller owns the ordered assessment windows and the availability time of
    every query. Each window selects one policy using only its declared
    training queries, applies that fixed policy to later held-out queries, and
    retains the exact rankings and evaluation. All held-out windows are then
    combined in original input-query order. A separate all-data tuning report
    is returned as future policy advice, not out-of-sample evidence.
    """
    validated_cutoff = _require_positive_integer(cutoff, "cutoff")
    query_ids = tuple(channel_results_by_query)

    # Reuse the complete-set evaluation boundary before any temporal slicing.
    evaluate_rankings(
        {query_id: () for query_id in query_ids},
        relevance_by_query,
        cutoff=validated_cutoff,
    )
    available_times = _normalize_available_times(
        query_ids, available_time_by_query
    )
    validated_windows, initial_training_query_ids = (
        _validate_window_structure(windows, query_ids)
    )
    temporal_bounds = _validate_temporal_order(
        validated_windows, available_times
    )

    window_reports = []
    out_of_sample_rankings_by_query: dict[
        QueryIdentifier, tuple[ItemIdentifier, ...]
    ] = {}
    for window, (
        training_available_time_max,
        held_out_available_time_min,
        held_out_available_time_max,
    ) in zip(validated_windows, temporal_bounds, strict=True):
        training_results = {
            query_id: channel_results_by_query[query_id]
            for query_id in window.training_query_ids
        }
        training_relevance = {
            query_id: relevance_by_query[query_id]
            for query_id in window.training_query_ids
        }
        tuning = tune_weighted_convex_fusion(
            training_results,
            training_relevance,
            candidate_channel_weights,
            cutoff=validated_cutoff,
            objective_name=objective_name,
        )
        selected_weights = dict(tuning.best_channel_weights)
        held_out_rankings = tuple(
            (
                query_id,
                tuple(
                    fused_item.item_id
                    for fused_item in weighted_convex_fuse(
                        channel_results_by_query[query_id],
                        selected_weights,
                        limit=validated_cutoff,
                    )
                ),
            )
            for query_id in window.held_out_query_ids
        )
        held_out_evaluation = evaluate_rankings(
            dict(held_out_rankings),
            {
                query_id: relevance_by_query[query_id]
                for query_id in window.held_out_query_ids
            },
            cutoff=validated_cutoff,
        )
        out_of_sample_rankings_by_query.update(held_out_rankings)
        window_reports.append(
            WeightedConvexBacktestWindow(
                window_id=window.window_id,
                training_query_ids=window.training_query_ids,
                held_out_query_ids=window.held_out_query_ids,
                training_available_time_max=training_available_time_max,
                held_out_available_time_min=held_out_available_time_min,
                held_out_available_time_max=held_out_available_time_max,
                tuning=tuning,
                held_out_rankings=held_out_rankings,
                held_out_evaluation=held_out_evaluation,
            )
        )

    out_of_sample_rankings = tuple(
        (query_id, out_of_sample_rankings_by_query[query_id])
        for query_id in query_ids
        if query_id in out_of_sample_rankings_by_query
    )
    out_of_sample_evaluation = evaluate_rankings(
        dict(out_of_sample_rankings),
        {
            query_id: relevance_by_query[query_id]
            for query_id, _ in out_of_sample_rankings
        },
        cutoff=validated_cutoff,
    )
    final_tuning = tune_weighted_convex_fusion(
        channel_results_by_query,
        relevance_by_query,
        candidate_channel_weights,
        cutoff=validated_cutoff,
        objective_name=objective_name,
    )
    return WeightedConvexBacktestReport(
        cutoff=validated_cutoff,
        objective_name=objective_name,
        initial_training_query_ids=initial_training_query_ids,
        windows=tuple(window_reports),
        out_of_sample_rankings=out_of_sample_rankings,
        out_of_sample_evaluation=out_of_sample_evaluation,
        final_tuning=final_tuning,
    )
