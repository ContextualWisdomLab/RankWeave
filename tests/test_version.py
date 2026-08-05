from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

import rankweave

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RELEASE_VERSION = "0.12.0"


def test_public_version_matches_release_version():
    assert rankweave.__version__ == EXPECTED_RELEASE_VERSION


def test_project_metadata_matches_public_version():
    project_metadata = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert project_metadata["project"]["version"] == rankweave.__version__
