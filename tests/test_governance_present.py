"""Test governance docs present."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_md_exists() -> None:
    assert (REPO_ROOT / "CONTRIBUTING.md").exists()


def test_maintainers_md_exists() -> None:
    assert (REPO_ROOT / "MAINTAINERS.md").exists()


def test_governance_docs_exist() -> None:
    g = REPO_ROOT / "docs" / "governance"
    assert (g / "contributor_agreement.md").exists()
    assert (g / "prompt_change_review.md").exists()


def test_contributing_mentions_golden_set_requirement() -> None:
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert "golden_set" in text
    assert "Apache-2.0" in text
