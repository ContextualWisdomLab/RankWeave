"""Strict portable artifacts for fixed RankWeave fusion policies."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from rankweave._validation import _require_positive_integer
from rankweave.ranked_list_fusion import (
    FusedScoredItem,
    FusedWeightedRankedItem,
    weighted_convex_fuse,
    weighted_reciprocal_rank_fuse,
)
from rankweave.score_fusion import _validate_convex_weights
from rankweave.tuning import (
    WeightedConvexTuningReport,
    WeightedRRFTuningReport,
)

ItemIdentifier = TypeVar("ItemIdentifier", bound=Hashable)
PolicyIdentifier = TypeVar("PolicyIdentifier", bound=Hashable)
QueryIdentifier = TypeVar("QueryIdentifier", bound=Hashable)

FUSION_POLICY_SCHEMA_VERSION = "rankweave.fusion-policy.v1"
WEIGHTED_CONVEX_POLICY_KIND = "weighted_convex"
WEIGHTED_RRF_POLICY_KIND = "weighted_rrf"

VALIDATION_TUNING_SOURCE = "validation_tuning"
BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE = (
    "blocked_cross_validation_final_tuning"
)
TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE = "temporal_backtest_final_tuning"
FULL_DATA_TUNING_SOURCE = "full_data_tuning"

_SUPPORTED_POLICY_KINDS = frozenset(
    {WEIGHTED_CONVEX_POLICY_KIND, WEIGHTED_RRF_POLICY_KIND}
)
_SUPPORTED_SELECTION_SOURCES = frozenset(
    {
        VALIDATION_TUNING_SOURCE,
        BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE,
        TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE,
        FULL_DATA_TUNING_SOURCE,
    }
)
_POLICY_FIELDS = frozenset(
    {
        "schema_version",
        "policy_kind",
        "policy_id",
        "channel_weights",
        "rank_constant_eta",
        "selection_source",
    }
)
_CHANNEL_WEIGHT_FIELDS = frozenset({"channel_name", "weight"})


def _require_printable_identifier(value: object, label: str) -> str:
    """Return one non-empty, unpadded printable identifier."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if not value or value != value.strip() or not value.isprintable():
        raise ValueError(
            f"{label} must be a non-empty unpadded printable string"
        )
    return value


def _require_weight(value: object, label: str) -> float:
    """Return one finite non-boolean weight in the closed unit interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite real number")
    numeric_value = float(value)
    if numeric_value != numeric_value or numeric_value in (
        float("inf"),
        float("-inf"),
    ):
        raise ValueError(f"{label} must be finite")
    if not 0.0 <= numeric_value <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return numeric_value


@dataclass(frozen=True)
class FusionPolicyChannelWeight:
    """One ordered fusion channel name and its fixed convex weight."""

    channel_name: str
    weight: float

    def __post_init__(self) -> None:
        """Validate and normalize the public channel-weight contract."""
        object.__setattr__(
            self,
            "channel_name",
            _require_printable_identifier(self.channel_name, "channel_name"),
        )
        object.__setattr__(
            self,
            "weight",
            _require_weight(
                self.weight,
                f"weight for channel {self.channel_name!r}",
            ),
        )


@dataclass(frozen=True)
class FusionPolicyArtifact:
    """One immutable deployable fixed-policy transport record."""

    schema_version: str
    policy_kind: str
    policy_id: str
    channel_weights: tuple[FusionPolicyChannelWeight, ...]
    rank_constant_eta: int | None
    selection_source: str

    def __post_init__(self) -> None:
        """Validate and snapshot the complete public artifact contract."""
        if self.schema_version != FUSION_POLICY_SCHEMA_VERSION:
            raise ValueError(
                "schema_version must be "
                f"{FUSION_POLICY_SCHEMA_VERSION!r}"
            )
        if self.policy_kind not in _SUPPORTED_POLICY_KINDS:
            raise ValueError(
                "policy_kind must be one of "
                f"{sorted(_SUPPORTED_POLICY_KINDS)!r}"
            )
        object.__setattr__(
            self,
            "policy_id",
            _require_printable_identifier(self.policy_id, "policy_id"),
        )

        try:
            channel_weights = tuple(self.channel_weights)
        except TypeError as exc:
            raise ValueError(
                "channel_weights must be an iterable of channel weights"
            ) from exc
        if not channel_weights:
            raise ValueError("channel_weights must contain at least one channel")
        if not all(
            isinstance(item, FusionPolicyChannelWeight)
            for item in channel_weights
        ):
            raise ValueError(
                "channel_weights must contain FusionPolicyChannelWeight records"
            )
        object.__setattr__(self, "channel_weights", channel_weights)

        ordered_weights: dict[str, float] = {}
        for channel_weight in channel_weights:
            if channel_weight.channel_name in ordered_weights:
                raise ValueError(
                    "channel_weights contain duplicate channel "
                    f"{channel_weight.channel_name!r}"
                )
            ordered_weights[channel_weight.channel_name] = channel_weight.weight
        _validate_convex_weights(ordered_weights)

        if self.policy_kind == WEIGHTED_CONVEX_POLICY_KIND:
            if self.rank_constant_eta is not None:
                raise ValueError(
                    "rank_constant_eta must be null for weighted_convex policy"
                )
        else:
            object.__setattr__(
                self,
                "rank_constant_eta",
                _require_positive_integer(
                    self.rank_constant_eta,
                    "rank_constant_eta",
                ),
            )
        if self.selection_source not in _SUPPORTED_SELECTION_SOURCES:
            raise ValueError(
                "selection_source must be one of "
                f"{sorted(_SUPPORTED_SELECTION_SOURCES)!r}"
            )


def _artifact_mapping(artifact: FusionPolicyArtifact) -> dict[str, Any]:
    """Return the fixed-order ordinary JSON projection for one artifact."""
    if not isinstance(artifact, FusionPolicyArtifact):
        raise ValueError("artifact must be a FusionPolicyArtifact")
    return {
        "schema_version": artifact.schema_version,
        "policy_kind": artifact.policy_kind,
        "policy_id": artifact.policy_id,
        "channel_weights": [
            {
                "channel_name": channel_weight.channel_name,
                "weight": channel_weight.weight,
            }
            for channel_weight in artifact.channel_weights
        ],
        "rank_constant_eta": artifact.rank_constant_eta,
        "selection_source": artifact.selection_source,
    }


def serialize_fusion_policy(artifact: FusionPolicyArtifact) -> bytes:
    """Serialize one artifact as deterministic compact UTF-8 JSON bytes."""
    document = json.dumps(
        _artifact_mapping(artifact),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return document.encode("utf-8") + b"\n"


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Construct one object while rejecting duplicate JSON member names."""
    result: dict[str, Any] = {}
    for member_name, member_value in pairs:
        if member_name in result:
            raise ValueError(f"duplicate JSON member {member_name!r}")
        result[member_name] = member_value
    return result


def _reject_json_constant(value: str) -> None:
    """Reject NaN and infinity extensions that are outside RFC 8259 JSON."""
    raise ValueError(f"non-standard JSON constant {value!r}")


def _require_exact_fields(
    value: Mapping[str, Any],
    required_fields: frozenset[str],
    label: str,
) -> None:
    """Require an object to contain exactly the declared public members."""
    actual_fields = frozenset(value)
    if actual_fields != required_fields:
        missing = sorted(required_fields - actual_fields)
        extra = sorted(actual_fields - required_fields)
        raise ValueError(
            f"{label} fields must be exactly the public contract; "
            f"missing={missing!r}, extra={extra!r}"
        )


def parse_fusion_policy(document: str) -> FusionPolicyArtifact:
    """Parse one strict untrusted JSON document into a frozen policy artifact."""
    if not isinstance(document, str):
        raise ValueError("document must be a string")
    try:
        parsed = json.loads(
            document,
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid fusion policy JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("fusion policy root must be a JSON object")
    _require_exact_fields(parsed, _POLICY_FIELDS, "fusion policy object")

    raw_channel_weights = parsed["channel_weights"]
    if not isinstance(raw_channel_weights, list):
        raise ValueError("channel_weights must be a JSON array")
    channel_weights = []
    for index, raw_channel_weight in enumerate(raw_channel_weights):
        if not isinstance(raw_channel_weight, dict):
            raise ValueError(
                f"channel weight at index {index} must be a JSON object"
            )
        _require_exact_fields(
            raw_channel_weight,
            _CHANNEL_WEIGHT_FIELDS,
            "channel weight",
        )
        channel_weights.append(
            FusionPolicyChannelWeight(
                channel_name=raw_channel_weight["channel_name"],
                weight=raw_channel_weight["weight"],
            )
        )

    return FusionPolicyArtifact(
        schema_version=parsed["schema_version"],
        policy_kind=parsed["policy_kind"],
        policy_id=parsed["policy_id"],
        channel_weights=tuple(channel_weights),
        rank_constant_eta=parsed["rank_constant_eta"],
        selection_source=parsed["selection_source"],
    )


def sha256_fusion_policy(artifact: FusionPolicyArtifact) -> str:
    """Return SHA-256 over the exact deterministic serialized policy bytes."""
    return hashlib.sha256(serialize_fusion_policy(artifact)).hexdigest()


def _policy_weights(
    channel_weights: Sequence[FusionPolicyChannelWeight],
) -> dict[str, float]:
    """Return an insertion-ordered mapping for native fusion APIs."""
    return {
        channel_weight.channel_name: channel_weight.weight
        for channel_weight in channel_weights
    }


def _require_transport_policy_id(
    selected_policy_id: object,
    policy_id: object,
) -> str:
    """Validate an explicit transport ID without silently stringifying IDs."""
    validated_policy_id = _require_printable_identifier(policy_id, "policy_id")
    if isinstance(selected_policy_id, str) and (
        validated_policy_id != selected_policy_id
    ):
        raise ValueError(
            "policy_id must match the selected string tuning policy identifier"
        )
    return validated_policy_id


def fusion_policy_from_convex_tuning(
    report: WeightedConvexTuningReport[PolicyIdentifier, QueryIdentifier],
    *,
    policy_id: str,
    selection_source: str,
) -> FusionPolicyArtifact:
    """Create a weighted-convex artifact from native selected tuning evidence."""
    if not isinstance(report, WeightedConvexTuningReport):
        raise ValueError("report must be a WeightedConvexTuningReport")
    return FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind=WEIGHTED_CONVEX_POLICY_KIND,
        policy_id=_require_transport_policy_id(
            report.best_policy_id,
            policy_id,
        ),
        channel_weights=tuple(
            FusionPolicyChannelWeight(channel_name, channel_weight)
            for channel_name, channel_weight in report.best_channel_weights
        ),
        rank_constant_eta=None,
        selection_source=selection_source,
    )


def fusion_policy_from_rrf_tuning(
    report: WeightedRRFTuningReport[PolicyIdentifier, QueryIdentifier],
    *,
    policy_id: str,
    selection_source: str,
) -> FusionPolicyArtifact:
    """Create a weighted-RRF artifact from native selected tuning evidence."""
    if not isinstance(report, WeightedRRFTuningReport):
        raise ValueError("report must be a WeightedRRFTuningReport")
    return FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind=WEIGHTED_RRF_POLICY_KIND,
        policy_id=_require_transport_policy_id(
            report.best_policy_id,
            policy_id,
        ),
        channel_weights=tuple(
            FusionPolicyChannelWeight(channel_name, channel_weight)
            for channel_name, channel_weight in report.best_channel_weights
        ),
        rank_constant_eta=report.rank_constant_eta,
        selection_source=selection_source,
    )


def apply_fusion_policy(
    artifact: FusionPolicyArtifact,
    *,
    channel_results: Mapping[
        str, Sequence[tuple[ItemIdentifier, float]]
    ]
    | None = None,
    channel_rankings: Mapping[str, Sequence[ItemIdentifier]] | None = None,
    limit: int | None = None,
) -> list[
    FusedScoredItem[ItemIdentifier] | FusedWeightedRankedItem[ItemIdentifier]
]:
    """Apply one artifact through the matching native complete-list fusion API."""
    if not isinstance(artifact, FusionPolicyArtifact):
        raise ValueError("artifact must be a FusionPolicyArtifact")
    if (channel_results is None) == (channel_rankings is None):
        raise ValueError("exactly one compatible input must be provided")
    channel_weights = _policy_weights(artifact.channel_weights)
    if artifact.policy_kind == WEIGHTED_CONVEX_POLICY_KIND:
        if channel_results is None:
            raise ValueError(
                "weighted_convex policy requires channel_results"
            )
        return weighted_convex_fuse(
            channel_results,
            channel_weights,
            limit=limit,
        )
    if channel_rankings is None:
        raise ValueError("weighted_rrf policy requires channel_rankings")
    return weighted_reciprocal_rank_fuse(
        channel_rankings,
        channel_weights,
        rank_constant_eta=artifact.rank_constant_eta,
        limit=limit,
    )
