"""A1 — the wired research ledger (one append-only ledger, typed records).

The compounding spine: hypotheses (incl. falsified), tournament rounds,
and generic typed records persist across runs so run N+1 starts warm and a
prior-falsified direction is never silently re-proposed. Append-only =
Darwin's rule made structural (the fact AGAINST the leading hypothesis is
preserved, not overwritten).
"""
from __future__ import annotations

from opl_cancer.memory.schemas import (
    ClaimLayer,
    Hypothesis,
    TournamentOutcome,
    TournamentRound,
)
from opl_cancer.memory.store import ProjectMemoryStore


def _store(tmp_path) -> ProjectMemoryStore:
    return ProjectMemoryStore(tmp_path / "memory" / "ledger.db")


def test_save_and_query_hypothesis_roundtrips(tmp_path):
    store = _store(tmp_path)
    h = Hypothesis(id="H1", text="MTAP-loss → PRMT5 synthetic lethality")
    store.save_hypothesis(h, run_id="run-001")

    got = store.query_hypotheses(run_id="run-001")
    assert len(got) == 1
    assert got[0].id == "H1"
    assert got[0].text.startswith("MTAP-loss")


def test_ledger_is_append_only_falsified_preserved(tmp_path):
    """Darwin's rule: the falsified version is preserved beside the active one."""
    store = _store(tmp_path)
    store.save_hypothesis(Hypothesis(id="H1", text="t", status="active"), run_id="r1")
    store.save_hypothesis(Hypothesis(id="H1", text="t", status="falsified"), run_id="r2")

    all_h = store.query_hypotheses()  # no run filter → full history
    statuses = [h.status for h in all_h if h.id == "H1"]
    assert "active" in statuses and "falsified" in statuses

    # A later run can see the direction was already falsified for this patient.
    falsified = store.query_hypotheses(status="falsified")
    assert any(h.id == "H1" for h in falsified)


def test_save_and_query_tournament_round(tmp_path):
    store = _store(tmp_path)
    rnd = TournamentRound(
        round_id="t-1",
        wave_index=2,
        participants=["H1", "H2"],
        pairings=[("H1", "H2")],
        outcomes=[TournamentOutcome(a="H1", b="H2", winner="A", reason="mechanism")],
    )
    store.save_tournament_round(rnd, run_id="run-001")

    got = store.query_tournament_rounds(run_id="run-001")
    assert len(got) == 1
    assert got[0].round_id == "t-1"
    assert got[0].outcomes[0].winner == "A"


def test_generic_append_ledger_and_counts(tmp_path):
    store = _store(tmp_path)
    assert store.has_ledger_rows("run-x") is False
    store.append_ledger("outcome", "O1", {"verdict": "team_was_right"}, run_id="run-x")
    store.append_ledger("failure_pile", "P1", {"size": 3}, run_id="run-x")

    assert store.has_ledger_rows("run-x") is True
    assert store.ledger_count(run_id="run-x") == 2
    assert store.ledger_count(run_id="run-x", record_type="outcome") == 1
    rows = store.ledger_rows(record_type="outcome", run_id="run-x")
    assert rows[0]["verdict"] == "team_was_right"


def test_ledger_does_not_disturb_insights_table(tmp_path):
    """The ledger is additive — the existing insights store still works."""
    store = _store(tmp_path)
    # query_by_layer on a fresh store should simply be empty, not error.
    assert store.query_by_layer(ClaimLayer.ESTABLISHED) == []
    store.append_ledger("hypothesis", "H9", {"x": 1}, run_id="r")
    assert store.query_by_layer(ClaimLayer.ESTABLISHED) == []
