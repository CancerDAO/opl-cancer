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


def test_readme_has_roadmap_section() -> None:
    """Iter 16: Roadmap section lists v1.1+ planned items."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "## Roadmap" in text, "README missing '## Roadmap' heading"
    # Roadmap must mention each of the 4 promised v1.1+ themes.
    for token in ("BioLinkX", "cancer types", "Web UI", "Multi-language"):
        assert token in text, f"README Roadmap missing token {token!r}"


def test_disclaimer_has_v1_release_and_emergency_notice() -> None:
    """Iter 16: DISCLAIMER carries v1.x scope + emergency-number guidance + jurisdictional notice."""
    text = (REPO_ROOT / "DISCLAIMER.md").read_text()
    assert "v1.x" in text
    assert "120" in text and "911" in text  # CN + US emergency numbers
    assert "WITHOUT WARRANTY" in text
    assert "Jurisdictional notice" in text
