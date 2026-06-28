"""C1 / ADR-0031 — the journal records killed candidates (real tournament kills).

Isolated test on the pure Journal API (no LLM import), so it runs in the patient
repo suite even while the orchestrator's LLM-coupled tests are parked.
"""
from __future__ import annotations

from opl_cancer.orchestrator.best_first_journal import Journal, Node


def test_killed_candidates_reports_pruned_nodes():
    j = Journal()
    j.add_node(Node(id="h1", parent_id=None, payload={"hypothesis_id": "h1"}, metric=1300.0, status="alive"))
    j.add_node(Node(id="h2", parent_id=None, payload={"hypothesis_id": "h2"}, metric=1100.0, status="alive"))
    j.add_node(Node(id="h3", parent_id=None, payload={"hypothesis_id": "h3"}, metric=1050.0, status="alive"))

    pruned = j.prune_below(1200.0)  # h2 + h3 are dominated
    assert {n.id for n in pruned} == {"h2", "h3"}

    kills = j.killed_candidates()
    assert {k["hyp_id"] for k in kills} == {"h2", "h3"}
    assert all("kill_reason" in k and "final_elo" in k for k in kills)


def test_no_kills_when_nothing_pruned():
    j = Journal()
    j.add_node(Node(id="h1", parent_id=None, payload={"hypothesis_id": "h1"}, metric=1300.0, status="alive"))
    assert j.killed_candidates() == []
