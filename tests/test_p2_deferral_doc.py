"""Test that the P2 deferral doc accounts for all 6 P2 items from PRD."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFERRAL_DOC = REPO_ROOT / "docs" / "P2_DEFERRALS_v1.5.md"


def test_p2_deferral_doc_exists() -> None:
    assert DEFERRAL_DOC.exists()


def test_all_6_p2_items_accounted_for() -> None:
    content = DEFERRAL_DOC.read_text(encoding="utf-8")
    for p2_id in ("P2-1", "P2-2", "P2-3", "P2-4", "P2-5", "P2-6"):
        assert p2_id in content, f"P2 deferral doc missing {p2_id}"


def test_each_deferred_item_has_rationale_and_hook() -> None:
    content = DEFERRAL_DOC.read_text(encoding="utf-8")
    # The 3 deferred items must each have a "Rationale" + "v1.6 hook"
    assert content.count("**Rationale:**") == 3
    assert content.count("**v1.6 hook:**") == 3


def test_shipped_items_marked() -> None:
    content = DEFERRAL_DOC.read_text(encoding="utf-8")
    assert "SHIPPED" in content
    # At least P2-3 shipped fully (plan-narration)
    assert "P2-3" in content and "SHIPPED" in content.split("P2-3")[1].split("\n", 1)[0]
