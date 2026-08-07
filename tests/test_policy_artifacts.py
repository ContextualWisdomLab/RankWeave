import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from rankweave import (
    FusionPolicyArtifact,
    FusionPolicyChannelWeight,
    WeightedConvexTuningReport,
    WeightedRRFTuningReport,
    apply_fusion_policy,
    fusion_policy_from_convex_tuning,
    fusion_policy_from_rrf_tuning,
    parse_fusion_policy,
    serialize_fusion_policy,
    sha256_fusion_policy,
    tune_weighted_convex_fusion,
    tune_weighted_reciprocal_rank_fusion,
    weighted_convex_fuse,
    weighted_reciprocal_rank_fuse,
)
from rankweave.policy_artifacts import (
    BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE,
    FUSION_POLICY_SCHEMA_VERSION,
    FULL_DATA_TUNING_SOURCE,
    TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE,
    VALIDATION_TUNING_SOURCE,
    WEIGHTED_CONVEX_POLICY_KIND,
    WEIGHTED_RRF_POLICY_KIND,
)


def _convex_artifact():
    return FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind=WEIGHTED_CONVEX_POLICY_KIND,
        policy_id="lexical-heavy",
        channel_weights=(
            FusionPolicyChannelWeight("lexical", 0.8),
            FusionPolicyChannelWeight("dense", 0.2),
        ),
        rank_constant_eta=None,
        selection_source=VALIDATION_TUNING_SOURCE,
    )


def _rrf_artifact():
    return FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind=WEIGHTED_RRF_POLICY_KIND,
        policy_id="dense-heavy",
        channel_weights=(
            FusionPolicyChannelWeight("lexical", 0.25),
            FusionPolicyChannelWeight("dense", 0.75),
        ),
        rank_constant_eta=17,
        selection_source=BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE,
    )


def _convex_tuning(policy_ids=("dense-heavy", "lexical-heavy")):
    return tune_weighted_convex_fusion(
        {
            "q1": {
                "lexical": (("a", 1.0), ("x", 0.0)),
                "dense": (("x", 1.0), ("a", 0.0)),
            },
            "q2": {
                "lexical": (("b", 1.0), ("y", 0.0)),
                "dense": (("y", 1.0), ("b", 0.0)),
            },
        },
        {"q1": {"a": 1.0}, "q2": {"b": 1.0}},
        {
            policy_ids[0]: {"lexical": 0.1, "dense": 0.9},
            policy_ids[1]: {"lexical": 0.9, "dense": 0.1},
        },
        cutoff=1,
    )


def _rrf_tuning(policy_ids=("dense-heavy", "lexical-heavy")):
    return tune_weighted_reciprocal_rank_fusion(
        {
            "q1": {"lexical": ("a", "x"), "dense": ("x", "a")},
            "q2": {"lexical": ("b", "y"), "dense": ("y", "b")},
        },
        {"q1": {"a": 1.0}, "q2": {"b": 1.0}},
        {
            policy_ids[0]: {"lexical": 0.1, "dense": 0.9},
            policy_ids[1]: {"lexical": 0.9, "dense": 0.1},
        },
        cutoff=1,
        rank_constant_eta=17,
    )


def test_policy_records_are_frozen_and_preserve_channel_order():
    artifact = _convex_artifact()

    assert artifact.schema_version == FUSION_POLICY_SCHEMA_VERSION
    assert artifact.policy_kind == WEIGHTED_CONVEX_POLICY_KIND
    assert tuple(item.channel_name for item in artifact.channel_weights) == (
        "lexical",
        "dense",
    )
    with pytest.raises(FrozenInstanceError):
        artifact.policy_id = "changed"
    with pytest.raises(FrozenInstanceError):
        artifact.channel_weights[0].weight = 0.1


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": "rankweave.fusion-policy.v2"}, "schema_version"),
        ({"policy_kind": "adaptive"}, "policy_kind"),
        ({"policy_id": ""}, "policy_id"),
        ({"policy_id": " padded"}, "policy_id"),
        ({"policy_id": "padded "}, "policy_id"),
        ({"policy_id": "bad\nidentifier"}, "policy_id"),
        ({"channel_weights": ()}, "channel_weights"),
        (
            {
                "channel_weights": (
                    FusionPolicyChannelWeight("lexical", 0.5),
                    FusionPolicyChannelWeight("lexical", 0.5),
                )
            },
            "duplicate channel",
        ),
        (
            {
                "channel_weights": (
                    FusionPolicyChannelWeight(" lexical", 0.5),
                    FusionPolicyChannelWeight("dense", 0.5),
                )
            },
            "channel_name",
        ),
        (
            {
                "channel_weights": (
                    FusionPolicyChannelWeight("lexical", 0.4),
                    FusionPolicyChannelWeight("dense", 0.4),
                )
            },
            "sum to 1",
        ),
        ({"rank_constant_eta": 60}, "rank_constant_eta must be null"),
        ({"selection_source": "unknown"}, "selection_source"),
    ],
)
def test_convex_policy_rejects_invalid_state(overrides, message):
    values = {
        "schema_version": FUSION_POLICY_SCHEMA_VERSION,
        "policy_kind": WEIGHTED_CONVEX_POLICY_KIND,
        "policy_id": "policy",
        "channel_weights": (
            FusionPolicyChannelWeight("lexical", 0.5),
            FusionPolicyChannelWeight("dense", 0.5),
        ),
        "rank_constant_eta": None,
        "selection_source": FULL_DATA_TUNING_SOURCE,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        FusionPolicyArtifact(**values)


@pytest.mark.parametrize(
    ("eta", "message"),
    [
        (None, "positive integer"),
        (0, "positive integer"),
        (-1, "positive integer"),
        (True, "positive integer"),
        (1.5, "positive integer"),
    ],
)
def test_rrf_policy_requires_positive_non_boolean_eta(eta, message):
    with pytest.raises(ValueError, match=message):
        FusionPolicyArtifact(
            schema_version=FUSION_POLICY_SCHEMA_VERSION,
            policy_kind=WEIGHTED_RRF_POLICY_KIND,
            policy_id="policy",
            channel_weights=(FusionPolicyChannelWeight("dense", 1.0),),
            rank_constant_eta=eta,
            selection_source=TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE,
        )


@pytest.mark.parametrize(
    ("name", "weight", "message"),
    [
        ("", 1.0, "channel_name"),
        ("bad\tchannel", 1.0, "channel_name"),
        (1, 1.0, "channel_name"),
        ("dense", True, "weight"),
        ("dense", float("nan"), "finite"),
        ("dense", float("inf"), "finite"),
        ("dense", -0.1, "between 0 and 1"),
        ("dense", 1.1, "between 0 and 1"),
    ],
)
def test_channel_weight_rejects_invalid_state(name, weight, message):
    with pytest.raises(ValueError, match=message):
        FusionPolicyChannelWeight(name, weight)


def test_convex_policy_serialization_is_exact_utf8_and_round_trips():
    artifact = _convex_artifact()
    expected = (
        b'{"schema_version":"rankweave.fusion-policy.v1",'
        b'"policy_kind":"weighted_convex","policy_id":"lexical-heavy",'
        b'"channel_weights":[{"channel_name":"lexical","weight":0.8},'
        b'{"channel_name":"dense","weight":0.2}],'
        b'"rank_constant_eta":null,'
        b'"selection_source":"validation_tuning"}\n'
    )

    serialized = serialize_fusion_policy(artifact)

    assert serialized == expected
    parsed = parse_fusion_policy(serialized.decode("utf-8"))
    assert parsed == artifact
    assert serialize_fusion_policy(parsed) == serialized


def test_policy_serialization_preserves_unicode_without_ascii_escaping():
    artifact = FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind=WEIGHTED_CONVEX_POLICY_KIND,
        policy_id="한국어-정책",
        channel_weights=(FusionPolicyChannelWeight("의미검색", 1.0),),
        rank_constant_eta=None,
        selection_source=FULL_DATA_TUNING_SOURCE,
    )

    serialized = serialize_fusion_policy(artifact)

    assert "한국어-정책".encode() in serialized
    assert "의미검색".encode() in serialized
    assert b"\\u" not in serialized


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("[]", "root must be a JSON object"),
        ("null", "root must be a JSON object"),
        ("{", "invalid fusion policy JSON"),
        (
            '{"schema_version":"rankweave.fusion-policy.v1",'
            '"schema_version":"rankweave.fusion-policy.v1"}',
            "duplicate JSON member",
        ),
        (
            '{"schema_version":"rankweave.fusion-policy.v1",'
            '"policy_kind":"weighted_convex","policy_id":"p",'
            '"channel_weights":[{"channel_name":"dense","weight":NaN}],'
            '"rank_constant_eta":null,"selection_source":"full_data_tuning"}',
            "non-standard JSON constant",
        ),
        (
            '{"schema_version":"rankweave.fusion-policy.v1",'
            '"policy_kind":"weighted_convex","policy_id":"p",'
            '"channel_weights":[{"channel_name":"dense","weight":1.0}],'
            '"rank_constant_eta":null,"selection_source":"full_data_tuning",'
            '"extra":true}',
            "object fields",
        ),
        (
            '{"schema_version":"rankweave.fusion-policy.v1",'
            '"policy_kind":"weighted_convex","policy_id":"p",'
            '"channel_weights":[{"channel_name":"dense","weight":1.0,'
            '"extra":true}],"rank_constant_eta":null,'
            '"selection_source":"full_data_tuning"}',
            "channel weight fields",
        ),
    ],
)
def test_parse_policy_rejects_hostile_or_malformed_json(document, message):
    with pytest.raises(ValueError, match=message):
        parse_fusion_policy(document)


def test_parse_policy_requires_text_input():
    with pytest.raises(ValueError, match="document must be a string"):
        parse_fusion_policy(b"{}")


def test_policy_sha256_hashes_exact_serialized_bytes():
    artifact = _convex_artifact()
    expected = hashlib.sha256(serialize_fusion_policy(artifact)).hexdigest()

    assert sha256_fusion_policy(artifact) == expected
    assert len(expected) == 64
    assert sha256_fusion_policy(_rrf_artifact()) != expected


@pytest.mark.parametrize(
    "field_change",
    [
        "channel_order",
        "weight",
        "eta",
        "policy_id",
        "selection_source",
    ],
)
def test_policy_sha256_changes_for_every_material_contract_change(field_change):
    artifact = _rrf_artifact()
    values = {
        "schema_version": artifact.schema_version,
        "policy_kind": artifact.policy_kind,
        "policy_id": artifact.policy_id,
        "channel_weights": artifact.channel_weights,
        "rank_constant_eta": artifact.rank_constant_eta,
        "selection_source": artifact.selection_source,
    }
    if field_change == "channel_order":
        values["channel_weights"] = tuple(reversed(artifact.channel_weights))
    elif field_change == "weight":
        values["channel_weights"] = (
            FusionPolicyChannelWeight("lexical", 0.5),
            FusionPolicyChannelWeight("dense", 0.5),
        )
    elif field_change == "eta":
        values["rank_constant_eta"] = 18
    elif field_change == "policy_id":
        values["policy_id"] = "changed"
    else:
        values["selection_source"] = TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE

    changed = FusionPolicyArtifact(**values)

    assert sha256_fusion_policy(changed) != sha256_fusion_policy(artifact)


def test_convex_tuning_constructor_preserves_selected_policy_and_weight_order():
    report = _convex_tuning()
    assert isinstance(report, WeightedConvexTuningReport)

    artifact = fusion_policy_from_convex_tuning(
        report,
        policy_id="lexical-heavy",
        selection_source=VALIDATION_TUNING_SOURCE,
    )

    assert artifact.policy_kind == WEIGHTED_CONVEX_POLICY_KIND
    assert artifact.policy_id == report.best_policy_id == "lexical-heavy"
    assert tuple(
        (item.channel_name, item.weight) for item in artifact.channel_weights
    ) == report.best_channel_weights
    assert artifact.rank_constant_eta is None


def test_rrf_tuning_constructor_preserves_selected_policy_weights_and_eta():
    report = _rrf_tuning()
    assert isinstance(report, WeightedRRFTuningReport)

    artifact = fusion_policy_from_rrf_tuning(
        report,
        policy_id="lexical-heavy",
        selection_source=BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE,
    )

    assert artifact.policy_kind == WEIGHTED_RRF_POLICY_KIND
    assert artifact.policy_id == report.best_policy_id == "lexical-heavy"
    assert tuple(
        (item.channel_name, item.weight) for item in artifact.channel_weights
    ) == report.best_channel_weights
    assert artifact.rank_constant_eta == 17


def test_string_tuning_policy_id_cannot_be_relabelled_silently():
    report = _convex_tuning()

    with pytest.raises(ValueError, match="policy_id must match"):
        fusion_policy_from_convex_tuning(
            report,
            policy_id="renamed",
            selection_source=VALIDATION_TUNING_SOURCE,
        )


def test_non_string_tuning_policy_id_requires_explicit_transport_identifier():
    report = _rrf_tuning(policy_ids=(1, 2))

    artifact = fusion_policy_from_rrf_tuning(
        report,
        policy_id="policy-two",
        selection_source=FULL_DATA_TUNING_SOURCE,
    )

    assert report.best_policy_id == 2
    assert artifact.policy_id == "policy-two"


@pytest.mark.parametrize(
    ("builder", "report", "message"),
    [
        (fusion_policy_from_convex_tuning, object(), "WeightedConvexTuningReport"),
        (fusion_policy_from_rrf_tuning, object(), "WeightedRRFTuningReport"),
    ],
)
def test_tuning_constructors_reject_wrong_report_types(builder, report, message):
    with pytest.raises(ValueError, match=message):
        builder(
            report,
            policy_id="policy",
            selection_source=FULL_DATA_TUNING_SOURCE,
        )


def test_apply_convex_policy_matches_native_fusion_exactly():
    artifact = _convex_artifact()
    channel_results = {
        "lexical": (("a", 1.0), ("b", 0.2)),
        "dense": (("b", 0.9), ("a", 0.1)),
    }

    actual = apply_fusion_policy(
        artifact,
        channel_results=channel_results,
        limit=2,
    )
    expected = weighted_convex_fuse(
        channel_results,
        {"lexical": 0.8, "dense": 0.2},
        limit=2,
    )

    assert actual == expected


def test_apply_rrf_policy_matches_native_fusion_exactly():
    artifact = _rrf_artifact()
    channel_rankings = {
        "lexical": ("a", "b"),
        "dense": ("b", "a"),
    }

    actual = apply_fusion_policy(
        artifact,
        channel_rankings=channel_rankings,
        limit=2,
    )
    expected = weighted_reciprocal_rank_fuse(
        channel_rankings,
        {"lexical": 0.25, "dense": 0.75},
        rank_constant_eta=17,
        limit=2,
    )

    assert actual == expected


@pytest.mark.parametrize(
    ("artifact", "arguments", "message"),
    [
        (_convex_artifact(), {}, "exactly one compatible input"),
        (
            _convex_artifact(),
            {"channel_results": {}, "channel_rankings": {}},
            "exactly one compatible input",
        ),
        (
            _convex_artifact(),
            {"channel_rankings": {"dense": ("a",)}},
            "weighted_convex policy requires channel_results",
        ),
        (
            _rrf_artifact(),
            {"channel_results": {"dense": (("a", 1.0),)}},
            "weighted_rrf policy requires channel_rankings",
        ),
    ],
)
def test_apply_policy_rejects_incompatible_input_modes(
    artifact, arguments, message
):
    with pytest.raises(ValueError, match=message):
        apply_fusion_policy(artifact, **arguments)


def test_serialized_policy_is_ordinary_json_not_an_authentication_claim():
    document = json.loads(serialize_fusion_policy(_convex_artifact()))

    assert set(document) == {
        "schema_version",
        "policy_kind",
        "policy_id",
        "channel_weights",
        "rank_constant_eta",
        "selection_source",
    }
    for forbidden in (
        "signature",
        "attestation",
        "provenance",
        "publisher",
        "quality_score",
        "p_value",
    ):
        assert forbidden not in document
