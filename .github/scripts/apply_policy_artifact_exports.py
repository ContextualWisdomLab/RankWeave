"""Apply the reviewed RankWeave fusion-policy root exports."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "src/rankweave/__init__.py"
content = PATH.read_text(encoding="utf-8")

anchor = """from rankweave.comparison import (
"""
import_block = """from rankweave.policy_artifacts import (
    BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE,
    FUSION_POLICY_SCHEMA_VERSION,
    FULL_DATA_TUNING_SOURCE,
    TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE,
    VALIDATION_TUNING_SOURCE,
    WEIGHTED_CONVEX_POLICY_KIND,
    WEIGHTED_RRF_POLICY_KIND,
    FusionPolicyArtifact,
    FusionPolicyChannelWeight,
    apply_fusion_policy,
    fusion_policy_from_convex_tuning,
    fusion_policy_from_rrf_tuning,
    parse_fusion_policy,
    serialize_fusion_policy,
    sha256_fusion_policy,
)
"""
if import_block not in content:
    if content.count(anchor) != 1:
        raise SystemExit("package root comparison import anchor changed")
    content = content.replace(anchor, import_block + anchor, 1)

all_anchor = '    "ArtifactVerificationReport",\n'
all_block = """    "BLOCKED_CROSS_VALIDATION_FINAL_TUNING_SOURCE",
    "FUSION_POLICY_SCHEMA_VERSION",
    "FULL_DATA_TUNING_SOURCE",
    "FusionPolicyArtifact",
    "FusionPolicyChannelWeight",
"""
if all_block not in content:
    if content.count(all_anchor) != 1:
        raise SystemExit("package root __all__ artifact anchor changed")
    content = content.replace(all_anchor, all_anchor + all_block, 1)

second_anchor = '    "TWO_SIDED_ALTERNATIVE",\n'
second_block = """    "TEMPORAL_BACKTEST_FINAL_TUNING_SOURCE",
    "VALIDATION_TUNING_SOURCE",
    "WEIGHTED_CONVEX_POLICY_KIND",
    "WEIGHTED_RRF_POLICY_KIND",
"""
if second_block not in content:
    if content.count(second_anchor) != 1:
        raise SystemExit("package root __all__ alternative anchor changed")
    content = content.replace(second_anchor, second_anchor + second_block, 1)

function_anchor = '    "available_report_schemas",\n'
function_block = """    "apply_fusion_policy",
"""
if function_block not in content:
    if content.count(function_anchor) != 1:
        raise SystemExit("package root __all__ function anchor changed")
    content = content.replace(function_anchor, function_block + function_anchor, 1)

constructor_anchor = '    "format_trec_run",\n'
constructor_block = """    "fusion_policy_from_convex_tuning",
    "fusion_policy_from_rrf_tuning",
"""
if constructor_block not in content:
    if content.count(constructor_anchor) != 1:
        raise SystemExit("package root __all__ constructor anchor changed")
    content = content.replace(
        constructor_anchor,
        constructor_anchor + constructor_block,
        1,
    )

parse_anchor = '    "parse_trec_qrels",\n'
parse_block = """    "parse_fusion_policy",
"""
if parse_block not in content:
    if content.count(parse_anchor) != 1:
        raise SystemExit("package root __all__ parse anchor changed")
    content = content.replace(parse_anchor, parse_block + parse_anchor, 1)

serialize_anchor = '    "reciprocal_rank_fusion_score",\n'
serialize_block = """    "serialize_fusion_policy",
    "sha256_fusion_policy",
"""
if serialize_block not in content:
    if content.count(serialize_anchor) != 1:
        raise SystemExit("package root __all__ serialization anchor changed")
    content = content.replace(
        serialize_anchor,
        serialize_anchor + serialize_block,
        1,
    )

PATH.write_text(content, encoding="utf-8")
