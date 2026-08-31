from io import BytesIO
from pathlib import Path
from tarfile import TarInfo
from tarfile import open as open_tarfile
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from scripts.verify_release_archives import (
    REQUIRED_SOURCE_MEMBERS,
    REQUIRED_WHEEL_MEMBERS,
    verify_release_archives,
)

VERSION = "0.18.0"


def _write_wheel(dist_dir: Path, *, omitted_member: str | None = None) -> None:
    wheel_path = (
        dist_dir / f"rankweave-{VERSION}-cp310-abi3-linux_x86_64.whl"
    )
    members = set(REQUIRED_WHEEL_MEMBERS)
    members.add("rankweave/_rankweave_core.abi3.so")
    if omitted_member is not None:
        members.remove(omitted_member)
    with ZipFile(wheel_path, "w", ZIP_DEFLATED) as archive:
        for member in sorted(members):
            archive.writestr(member, b"synthetic")


def _write_sdist(dist_dir: Path, *, omitted_member: str | None = None) -> None:
    source_path = dist_dir / f"rankweave-{VERSION}.tar.gz"
    members = set(REQUIRED_SOURCE_MEMBERS)
    if omitted_member is not None:
        members.remove(omitted_member)
    with open_tarfile(source_path, "w:gz") as archive:
        for member in sorted(members):
            payload = b"synthetic"
            member_info = TarInfo(f"rankweave-{VERSION}/{member}")
            member_info.size = len(payload)
            archive.addfile(member_info, BytesIO(payload))


def test_verify_release_archives_accepts_complete_native_archives(tmp_path):
    _write_wheel(tmp_path)
    _write_sdist(tmp_path)

    verify_release_archives(
        tmp_path,
        VERSION,
        expected_wheel_tags=("linux",),
        require_sdist=True,
    )


def test_verify_release_archives_rejects_missing_native_stub(tmp_path):
    _write_wheel(tmp_path, omitted_member="rankweave/_rankweave_core.pyi")

    with pytest.raises(ValueError, match="_rankweave_core.pyi"):
        verify_release_archives(
            tmp_path,
            VERSION,
            expected_wheel_tags=("linux",),
            require_sdist=False,
        )


def test_verify_release_archives_rejects_missing_cargo_manifest(tmp_path):
    _write_sdist(tmp_path, omitted_member="crates/rankweave-core/Cargo.toml")

    with pytest.raises(ValueError, match="rankweave-core/Cargo.toml"):
        verify_release_archives(
            tmp_path,
            VERSION,
            expected_wheel_tags=(),
            require_sdist=True,
        )


def test_verify_release_archives_rejects_wrong_platform_set(tmp_path):
    _write_wheel(tmp_path)

    with pytest.raises(ValueError, match="macosx"):
        verify_release_archives(
            tmp_path,
            VERSION,
            expected_wheel_tags=("macosx",),
            require_sdist=False,
        )
