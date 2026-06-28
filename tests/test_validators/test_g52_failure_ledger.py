"""G52 — the run must read its own failures (Ng's move), not just its successes.

C3 / ADR-0033. OPL has excellent per-claim gates and surfaces individual
disconfirmers, but nothing performs the Ng move: pull ALL of a run's failures
into one place, sort into root-cause piles, name the biggest, and flag whether a
top-3 conclusion rests on it. Without it, a conclusion built on a pile of
low-match cohorts + single-source trials + weakened hypotheses reaches the
patient all-gates-green. G52 BLOCKS a run that reached validation but produced no
failure_ledger.json. Machine-verifiable (artifact exists + structured).
"""
from __future__ import annotations

import json

from opl_cancer.validators.gates.g52_failure_ledger import G52FailureLedgerGate
from opl_cancer.validators.mechanical_gates import GateStatus


def _run(tmp_path, *, wave4=True, ledger=None):
    run_root = tmp_path / "triggers" / "run-001"
    run_root.mkdir(parents=True)
    if wave4:
        (run_root / "wave4_validation.json").write_text(
            json.dumps({"validations": [{"id": "H1", "verdict": "falsified"}]}),
            encoding="utf-8",
        )
    if ledger is not None:
        (run_root / "failure_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    return run_root


def test_skip_when_run_did_not_reach_validation(tmp_path):
    run_root = _run(tmp_path, wave4=False)
    res = G52FailureLedgerGate().check({"run_root": str(run_root)})
    assert res.status == GateStatus.SKIP


def test_block_when_validation_ran_but_no_failure_ledger(tmp_path):
    run_root = _run(tmp_path, wave4=True, ledger=None)
    res = G52FailureLedgerGate().check({"run_root": str(run_root)})
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_failure_ledger_malformed(tmp_path):
    run_root = _run(tmp_path, wave4=True, ledger={"note": "oops, no piles key"})
    res = G52FailureLedgerGate().check({"run_root": str(run_root)})
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_pass_when_failure_ledger_present_with_piles(tmp_path):
    ledger = {
        "piles": [
            {"root_cause": "single-source trial data", "size": 4, "items": ["t1", "t2"]},
            {"root_cause": "low subgroup match", "size": 2, "items": ["c1"]},
        ],
        "biggest_pile": "single-source trial data",
        "conclusions_at_risk": [],
    }
    run_root = _run(tmp_path, wave4=True, ledger=ledger)
    res = G52FailureLedgerGate().check({"run_root": str(run_root)})
    assert res.status == GateStatus.PASS


def test_pass_when_clean_run_records_empty_piles(tmp_path):
    """A genuinely clean run still records an (empty) ledger — honest, not absent."""
    run_root = _run(tmp_path, wave4=True, ledger={"piles": [], "biggest_pile": None})
    res = G52FailureLedgerGate().check({"run_root": str(run_root)})
    assert res.status == GateStatus.PASS
