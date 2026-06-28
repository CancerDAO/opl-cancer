"""G48 — research-delta: a run must produce net-new knowledge vs the prior run.

A3 / ADR-0028. Reframes the success metric from artifact-quality to research
progress. A cold re-run that re-derives an identical beautiful brief passes every
safety gate today — the canonical 'better report generator' failure. G48 FLAGs
(not blocks) a run with zero net-new knowledge vs the prior run on the same
patient: no new direction, no killed direction, no reality outcome. The
mechanical embodiment of 'OPL is a team, not an essayist.'
"""
from __future__ import annotations

from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.memory.store import ProjectMemoryStore
from opl_cancer.validators.gates.g48_research_delta import G48ResearchDeltaGate
from opl_cancer.validators.mechanical_gates import GateStatus


def _claim(db, run_id):
    return {"run_id": run_id, "memory_db": str(db)}


def test_skip_on_first_run_no_prior(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-1")
    res = G48ResearchDeltaGate().check(_claim(db, "run-1"))
    assert res.status == GateStatus.SKIP  # nothing to compare against


def test_pass_when_run_adds_a_new_direction(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-1")
    store.save_hypothesis(Hypothesis(id="H2", text="new direction"), run_id="run-2")
    res = G48ResearchDeltaGate().check(_claim(db, "run-2"))
    assert res.status == GateStatus.PASS


def test_pass_when_run_kills_a_direction(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-1")
    store.save_hypothesis(Hypothesis(id="H1", text="t", status="falsified"), run_id="run-2")
    res = G48ResearchDeltaGate().check(_claim(db, "run-2"))
    assert res.status == GateStatus.PASS


def test_flag_when_run_reproduces_prior_with_no_delta(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-1")
    # run-2 re-derives the same active direction, no kill, no outcome
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-2")
    res = G48ResearchDeltaGate().check(_claim(db, "run-2"))
    assert res.status == GateStatus.FAIL
    assert res.block is False  # FLAG, never blocks a legitimately stable follow-up


def test_pass_when_run_records_a_reality_outcome(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-1")
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-2")
    store.append_ledger("outcome", "O1", {"verdict": "team_was_right"}, run_id="run-2")
    res = G48ResearchDeltaGate().check(_claim(db, "run-2"))
    assert res.status == GateStatus.PASS
