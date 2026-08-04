"""Create a Git-free disposable copy of Git-visible repository files."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Sequence


class WorkspaceMaterializationError(ValueError):
    """Raised when a repository cannot be copied into a safe disposable tree."""


def _decode_git_path(raw_path: bytes) -> str:
    """Decode and validate one NUL-delimited path returned by Git."""
    try:
        path_text = raw_path.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WorkspaceMaterializationError("Git path is not strict UTF-8") from exc
    path = PurePosixPath(path_text)
    if not path_text or path.is_absolute() or ".." in path.parts:
        raise WorkspaceMaterializationError(f"invalid Git-visible path: {path_text!r}")
    return path_text


def _git_visible_paths(source: Path) -> tuple[str, ...]:
    """Return tracked and non-ignored untracked paths from ``source``."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return tuple(
        _decode_git_path(raw_path)
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    )


def materialize_workspace(source: Path, destination: Path) -> tuple[str, ...]:
    """Copy Git-visible regular files without repository metadata or symlinks."""
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    if (
        source == destination
        or source in destination.parents
        or destination in source.parents
    ):
        raise WorkspaceMaterializationError(
            "source and destination must be separate, non-nested trees"
        )
    if destination.exists():
        raise WorkspaceMaterializationError(
            f"destination already exists: {destination}"
        )

    paths = _git_visible_paths(source)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for path_text in paths:
            path = PurePosixPath(path_text)
            source_path = source.joinpath(*path.parts)
            info = source_path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise WorkspaceMaterializationError(
                    f"source path is not a regular file: {path_text}"
                )
            resolved = source_path.resolve(strict=True)
            if resolved != source and source not in resolved.parents:
                raise WorkspaceMaterializationError(
                    f"source path escapes the repository: {path_text}"
                )
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source_path.read_bytes())
            safe_mode = 0o755 if info.st_mode & stat.S_IXUSR else 0o644
            os.chmod(target, safe_mode)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return paths


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for workspace materialization."""
    parser = argparse.ArgumentParser(
        description=(
            "Copy tracked and non-ignored untracked regular files into "
            "a Git-free disposable directory."
        )
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Materialize a workspace and return a process exit code."""
    arguments = build_parser().parse_args(argv)
    paths = materialize_workspace(arguments.source, arguments.destination)
    print(f"materialized {len(paths)} Git-visible files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
