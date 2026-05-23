"""Test all 5 P0 ADRs exist."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_5_p0_adrs_exist() -> None:
    expected = {
        "0001-substrate-references.md",
        "0002-main-thread-only-dispatch.md",
        "0003-no-human-in-the-loop.md",
        "0004-task-primitive-grammar-in-experts.md",
        "0005-pi-single-conversational-surface.md",
    }
    actual = {p.name for p in (REPO_ROOT / "docs" / "adr").glob("*.md")}
    missing = expected - actual
    assert not missing, f"missing ADRs: {missing}"


def test_each_adr_has_required_sections() -> None:
    adr_dir = REPO_ROOT / "docs" / "adr"
    for adr in adr_dir.glob("000?-*.md"):
        text = adr.read_text()
        for section in ("## Status", "## Context", "## Decision", "## Consequences"):
            assert section in text, f"{adr.name} missing {section}"
