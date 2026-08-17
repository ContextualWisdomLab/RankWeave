from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPOSITORY_ROOT / "README.md"
HOURLY_LOOP_DOC = (
    REPOSITORY_ROOT / "docs/operations/hourly-commercialization-loop.md"
)


def _readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_readme_states_actual_pypi_publication_status():
    readme = _readme()

    assert "pip install rankweave" in readme
    assert "rankweave==0.1.0" in readme
    assert "PyPI still exposes only `0.1.0`" in readme or (
        "PyPI currently publishes only `0.1.0`" in readme
    )
    assert "pip install rankweave==0.18.0" not in readme
    assert "Until PyPI Trusted Publishing is configured" not in readme


def test_readme_documents_git_fallback_for_unpublished_versions():
    readme = _readme()

    assert (
        "git+https://github.com/ContextualWisdomLab/RankWeave.git" in readme
    )
    assert "v0.18.0" in readme


def test_readme_documents_published_sibling_library_contract():
    readme = _readme()

    assert "from rankweave import FusionSettings, fuse_channel_scores" in readme
    assert "Naruon" in readme
    assert "rankweave==0.1.0" in readme
    assert "LineageWeave" in readme
    assert "git commit" in readme.lower() or "git+https" in readme


def test_readme_keeps_hourly_loop_to_one_sentence_and_link():
    readme = _readme()

    assert "docs/operations/hourly-commercialization-loop.md" in readme
    for maintainer_only in (
        "exact-head",
        "do-not-merge",
        "writer-boundary",
        "OpenCode",
        "NVIDIA_NIM_API_KEY",
        "Hourly governed development loop",
    ):
        assert maintainer_only not in readme


def test_hourly_loop_operations_doc_retains_maintainer_contract():
    documentation = HOURLY_LOOP_DOC.read_text(encoding="utf-8")

    assert "Hourly commercialization loop" in documentation
    assert "NVIDIA_NIM_API_KEY" in documentation
    assert "OpenCode" in documentation
    assert "exact" in documentation.lower()
    assert "maintainer" in documentation.lower()
