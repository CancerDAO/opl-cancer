"""A2 — reality-outcome loop: score prior predictions against the patient's
ACTUAL clinical course, not against more literature.

This is the only ground-truth error signal in OPL. When a new scan / marker /
RECIST / toxicity arrives (the patient drops it into inbox/), the team scores its
prior ranked hypotheses/forecasts against THAT reality and records whether it was
right. Vivek's whole essay reduces to 'research speed is the speed at which you
discover you're wrong' — this is the channel through which reality can finally
tell OPL it was wrong.
"""
from __future__ import annotations

from opl_cancer.glue.outcome_reconcile import load_prior_predictions, persist_outcomes
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.memory.store import ProjectMemoryStore


def test_load_prior_predictions_returns_hypotheses(tmp_path):
    db = tmp_path / "m.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="sotorasib+pani will respond"), run_id="run-1")
    store.save_hypothesis(Hypothesis(id="H2", text="MTAP/PRMT5 candidate"), run_id="run-1")

    priors = load_prior_predictions(db)
    ids = {h["id"] for h in priors["hypotheses"]}
    assert ids == {"H1", "H2"}


def test_persist_outcomes_writes_to_ledger(tmp_path):
    db = tmp_path / "m.db"
    ProjectMemoryStore(db)
    outcomes = [
        {
            "id": "O-H1",
            "hypothesis_id": "H1",
            "pre_registered_direction": "partial response by RECIST",
            "real_world_datum": "CT 2026-06: -34% target lesions (PR)",
            "real_world_verdict": "confirmed",
            "team_was_right": True,
        },
        {
            "id": "O-H2",
            "hypothesis_id": "H2",
            "real_world_verdict": "not_yet_observable",
            "team_was_right": None,
        },
    ]
    n = persist_outcomes(db, "run-2", outcomes)
    assert n == 2

    store = ProjectMemoryStore(db)
    assert store.ledger_count(run_id="run-2", record_type="outcome") == 2
    rows = store.ledger_rows(record_type="outcome", run_id="run-2")
    assert any(r["real_world_verdict"] == "confirmed" for r in rows)


def test_persist_outcomes_empty_is_zero(tmp_path):
    db = tmp_path / "m.db"
    ProjectMemoryStore(db)
    assert persist_outcomes(db, "run-2", []) == 0
