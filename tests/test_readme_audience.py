from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"
CONTRIBUTING = PROJECT_ROOT / "CONTRIBUTING.md"
HOURLY_LOOP = PROJECT_ROOT / "docs/operations/hourly-commercialization-loop.md"


def test_readme_is_customer_facing_and_keeps_the_naruon_leaf_contract():
    readme = README.read_text(encoding="utf-8")

    assert "leaf product" in readme
    assert "does **not** require a Naruon checkout" in readme
    assert "https://github.com/ContextualWisdomLab/naruon" in readme
    assert "published contract" in readme
    assert "rankweave compare" in readme
    assert "available_report_schemas" in readme
    assert "NVIDIA_NIM_API_KEY" not in readme
    assert "OpenCode" not in readme
    assert "Hourly governed development loop" not in readme
    assert ".[dev]" not in readme


def test_contributor_and_operations_docs_own_automation_procedure():
    contributing = CONTRIBUTING.read_text(encoding="utf-8")
    hourly_loop = HOURLY_LOOP.read_text(encoding="utf-8")

    assert "Hourly governed development loop" in contributing
    assert "docs/operations/hourly-commercialization-loop.md" in contributing
    assert "NVIDIA_NIM_API_KEY" in contributing
    assert "customer and operator entry" in hourly_loop
    assert "CONTRIBUTING.md" in hourly_loop
