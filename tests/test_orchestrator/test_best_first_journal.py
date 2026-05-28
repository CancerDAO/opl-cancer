"""Tests for v2.5 best_first_journal — RFC 0001 §8 item 12 (Sakana borrow)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.orchestrator.best_first_journal import Journal, Node


def test_add_three_nodes_prunes_lowest_and_serializes(tmp_path: Path) -> None:
    """Hard-spec'd integration: record 3 nodes, prune lowest, serialize to JSONL."""
    j = Journal()
    j.add_node(Node(id="n1", parent_id=None, payload={"hypo": "h1"}, metric=0.2, status="alive"))
    j.add_node(Node(id="n2", parent_id="n1", payload={"hypo": "h2"}, metric=0.8, status="alive"))
    j.add_node(Node(id="n3", parent_id="n1", payload={"hypo": "h3"}, metric=0.5, status="alive"))

    best = j.best_node(by="metric")
    assert best.id == "n2"

    pruned = j.prune_below(threshold=0.3)
    assert {p.id for p in pruned} == {"n1"}
    assert j.find("n1").status == "pruned"
    assert j.find("n2").status == "alive"
    assert j.find("n3").status == "alive"

    out = tmp_path / "journal.jsonl"
    j.to_jsonl(out)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    ids = [p["id"] for p in parsed]
    statuses = {p["id"]: p["status"] for p in parsed}
    assert ids == ["n1", "n2", "n3"]
    assert statuses == {"n1": "pruned", "n2": "alive", "n3": "alive"}


def test_node_children_relation() -> None:
    j = Journal()
    j.add_node(Node(id="root", parent_id=None, payload={}, metric=1.0, status="alive"))
    j.add_node(Node(id="c1", parent_id="root", payload={}, metric=0.5, status="alive"))
    j.add_node(Node(id="c2", parent_id="root", payload={}, metric=0.7, status="alive"))
    children = j.children_of("root")
    assert {c.id for c in children} == {"c1", "c2"}


def test_module_carries_sakana_attribution_comment() -> None:
    """Per RFC 0001 §8 item 12: code MUST carry a license-respecting
    adaptation note crediting SakanaAI/AI-Scientist-v2."""
    src = Path("src/opl_cancer/orchestrator/best_first_journal.py").read_text(encoding="utf-8")
    assert "SakanaAI" in src
    assert "AI-Scientist-v2" in src
    # Must explicitly say we ONLY adopt the journal pattern, not their
    # unguarded LLM code-gen sandbox.
    assert "journal pattern" in src.lower()
    assert "Responsible-AI" in src or "license-respecting" in src


def test_journal_best_node_handles_empty() -> None:
    j = Journal()
    with pytest.raises(ValueError):
        j.best_node()


def test_duplicate_node_id_raises() -> None:
    j = Journal()
    j.add_node(Node(id="a", parent_id=None, payload={}, metric=0.1, status="alive"))
    with pytest.raises(ValueError):
        j.add_node(Node(id="a", parent_id=None, payload={}, metric=0.5, status="alive"))
