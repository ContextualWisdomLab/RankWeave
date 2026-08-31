"""Verify that RankWeave release archives contain the governed native package."""

from __future__ import annotations

import argparse
from pathlib import Path
from tarfile import open as open_tarfile
from zipfile import ZipFile

REQUIRED_WHEEL_MEMBERS = frozenset(
    {
        "rankweave/__init__.py",
        "rankweave/__main__.py",
        "rankweave/_rankweave_core.pyi",
        "rankweave/_validation.py",
        "rankweave/artifact_verification.py",
        "rankweave/cli.py",
        "rankweave/comparison.py",
        "rankweave/cross_validation.py",
        "rankweave/evaluation.py",
        "rankweave/py.typed",
        "rankweave/query_normalization.py",
        "rankweave/ranked_list_fusion.py",
        "rankweave/report_schemas.py",
        "rankweave/schemas/__init__.py",
        "rankweave/schemas/artifact-verification-v1.schema.json",
        "rankweave/schemas/trec-comparison-v1.schema.json",
        "rankweave/schemas/trec-comparison-v2.schema.json",
        "rankweave/schemas/trec-family-comparison-v1.schema.json",
        "rankweave/schemas/trec-family-comparison-v2.schema.json",
        "rankweave/score_fusion.py",
        "rankweave/semantic_index.py",
        "rankweave/semantic_vector_ranking.py",
        "rankweave/temporal_backtesting.py",
        "rankweave/trec.py",
        "rankweave/trec_comparison.py",
        "rankweave/trec_family_comparison.py",
        "rankweave/tuning.py",
    }
)

REQUIRED_SOURCE_MEMBERS = frozenset(
    {
        "Cargo.lock",
        "Cargo.toml",
        "CHANGELOG.md",
        "LICENSE",
        "README.md",
        "crates/rankweave-core/Cargo.toml",
        "crates/rankweave-core/src/lib.rs",
        "crates/rankweave-core/src/semantic_index.rs",
        "crates/rankweave-python/Cargo.toml",
        "crates/rankweave-python/src/lib.rs",
        "pyproject.toml",
        "src/rankweave/__init__.py",
        "src/rankweave/_rankweave_core.pyi",
        "src/rankweave/semantic_index.py",
        "src/rankweave/semantic_vector_ranking.py",
        "tests/test_version.py",
    }
)


def verify_release_archives(
    dist_dir: Path,
    version: str,
    *,
    expected_wheel_tags: tuple[str, ...],
    require_sdist: bool,
) -> None:
    """Fail unless release archives and their governed members are complete."""
    wheels = tuple(sorted(dist_dir.glob("rankweave-*.whl")))
    expected_wheel_count = len(expected_wheel_tags)
    if len(wheels) != expected_wheel_count:
        raise ValueError(
            f"release requires exactly {expected_wheel_count} wheel(s); "
            f"found {len(wheels)}"
        )

    expected_prefix = f"rankweave-{version}-cp310-abi3-"
    wheel_names = tuple(wheel.name for wheel in wheels)
    for wheel_name in wheel_names:
        if not wheel_name.startswith(expected_prefix):
            raise ValueError(f"unexpected stable-ABI wheel name: {wheel_name!r}")
    for required_tag in expected_wheel_tags:
        matches = tuple(name for name in wheel_names if required_tag in name)
        if len(matches) != 1:
            raise ValueError(
                f"release requires exactly one {required_tag!r} wheel; "
                f"found {len(matches)}"
            )

    for wheel in wheels:
        with ZipFile(wheel) as wheel_file:
            wheel_members = set(wheel_file.namelist())
        missing_wheel_members = REQUIRED_WHEEL_MEMBERS - wheel_members
        if missing_wheel_members:
            raise ValueError(
                f"wheel is missing: {sorted(missing_wheel_members)!r}"
            )
        if not any(
            member.startswith("rankweave/_rankweave_core.")
            and member.endswith((".so", ".pyd"))
            for member in wheel_members
        ):
            raise ValueError("wheel is missing the compiled RankWeave core")

    source_distributions = tuple(sorted(dist_dir.glob("rankweave-*.tar.gz")))
    expected_sdist_count = int(require_sdist)
    if len(source_distributions) != expected_sdist_count:
        raise ValueError(
            f"release requires exactly {expected_sdist_count} source "
            f"distribution(s); found {len(source_distributions)}"
        )
    if not require_sdist:
        return

    source_distribution = source_distributions[0]
    expected_sdist_name = f"rankweave-{version}.tar.gz"
    if source_distribution.name != expected_sdist_name:
        raise ValueError(
            f"unexpected source distribution name: {source_distribution.name!r}"
        )
    source_root = f"rankweave-{version}/"
    with open_tarfile(source_distribution, "r:gz") as archive:
        source_members = set(archive.getnames())
    required_source_members = {
        source_root + member for member in REQUIRED_SOURCE_MEMBERS
    }
    missing_source_members = required_source_members - source_members
    if missing_source_members:
        raise ValueError(
            f"source distribution is missing: {sorted(missing_source_members)!r}"
        )


def _parse_arguments() -> argparse.Namespace:
    """Parse the release-archive verification command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--wheel-tag",
        action="append",
        default=[],
        help="required unique substring in one stable-ABI wheel filename",
    )
    parser.add_argument("--require-sdist", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run release-archive verification from the command line."""
    arguments = _parse_arguments()
    try:
        verify_release_archives(
            arguments.dist_dir,
            arguments.version,
            expected_wheel_tags=tuple(arguments.wheel_tag),
            require_sdist=arguments.require_sdist,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
