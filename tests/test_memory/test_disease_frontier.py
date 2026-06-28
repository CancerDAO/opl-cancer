"""D4 — re-aim the learning loop at the disease frontier, fed by reality.

OPL's one real cross-run learning loop (evolution/) was being extracted out and,
even present, learned about OPL-the-software (proposals for the next DIFFERENT
patient). A research team's institutional memory is about the SCIENCE. This is
D4's core, built cleanly on the research ledger (A1) + reality outcomes (A2):
a digest aimed at THIS patient's disease frontier — what was killed (don't
re-propose), what reality verdicted, and what is still open to chase. It does NOT
touch the mid-extraction evolution/ engine (founder-gated); it is the verifiable
substance the re-aimed loop consumes.
"""
from __future__ import annotations

from opl_cancer.memory.disease_frontier import build_disease_frontier_digest
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.memory.store import ProjectMemoryStore


def test_digest_buckets_killed_open_and_reality(tmp_path):
    store = ProjectMemoryStore(tmp_path / "m.db")
    store.save_hypothesis(Hypothesis(id="H1", text="KRAS+EGFR combo"), run_id="r1")
    store.save_hypothesis(Hypothesis(id="H2", text="dead end", status="falsified"), run_id="r1")
    store.save_hypothesis(Hypothesis(id="H3", text="MTAP/PRMT5, not yet tested"), run_id="r1")
    store.append_ledger("outcome", "O1", {"hypothesis_id": "H1", "real_world_verdict": "confirmed",
                                          "team_was_right": True}, run_id="r2")
    store.append_ledger("failure_pile", "P1", {"root_cause": "single-source trials", "size": 4}, run_id="r1")

    d = build_disease_frontier_digest(store)

    assert "H2" in [h["id"] for h in d["killed_directions"]]      # don't re-propose
    assert any(o["real_world_verdict"] == "confirmed" for o in d["reality_verdicts"])
    assert d["systematic_gaps"][0]["root_cause"] == "single-source trials"
    open_ids = [h["id"] for h in d["open_frontier"]]
    assert "H3" in open_ids                                       # active + unscored → chase
    assert "H1" not in open_ids                                   # confirmed by reality → resolved, not open
    assert d["aimed_at"] == "patient_disease_frontier"            # NOT software


def test_empty_store_is_safe(tmp_path):
    store = ProjectMemoryStore(tmp_path / "m.db")
    d = build_disease_frontier_digest(store)
    assert d["killed_directions"] == [] and d["open_frontier"] == []
