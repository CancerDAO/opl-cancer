"""Test SKILL.md presence + required frontmatter."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_skill_md_exists() -> None:
    assert (REPO_ROOT / "SKILL.md").exists()


def test_skill_md_has_frontmatter() -> None:
    text = (REPO_ROOT / "SKILL.md").read_text()
    assert text.startswith("---\n")
    assert "name:" in text
    assert "description:" in text


def test_skill_md_description_includes_trigger_terms() -> None:
    text = (REPO_ROOT / "SKILL.md").read_text()
    expected_triggers = ["OPL", "cancer", "AI scientist team"]
    for trigger in expected_triggers:
        assert trigger in text, f"SKILL.md description missing trigger {trigger!r}"
