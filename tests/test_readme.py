"""Test README has required sections."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_required_sections() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    required = [
        "OPL for Cancer", "AI scientist team", "Apache-2.0",
        "Quick start", "Architecture", "Status", "Expert Roster",
        "Sid", "Henry",
    ]
    for r in required:
        assert r in text, f"README missing {r!r}"
