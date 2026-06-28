"""G54 — the research ledger must actually be written at attest.

A1/ADR-0027. The compounding spine is only real if the run persists what it
learned. If a run produced research artifacts (hypotheses / a delivered brief)
but wrote ZERO rows to the patient research ledger, the run did not compound —
the next run starts cold and can re-propose a falsified direction. That is a
verifiable fact (artifacts on disk vs ledger row count), so G54 BLOCKS.
"""
from __future__ import annotations

import json

from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.memory.store import ProjectMemoryStore
from opl_cancer.validators.gates.g54_memory_ledger_written import (
    G54MemoryLedgerWrittenGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _run_with_artifacts(tmp_path):
    run_root = tmp_path / "triggers" / "run-001"
    run_root.mkdir(parents=True)
    (run_root / "wave2_hypotheses.json").write_text(
        json.dumps([{"id": "H1", "text": "t"}]), encoding="utf-8"
    )
    return run_root


def test_pass_when_ledger_has_rows_for_run(tmp_path):
    run_root = _run_with_artifacts(tmp_path)
    db = tmp_path / "memory" / "ledger.db"
    store = ProjectMemoryStore(db)
    store.save_hypothesis(Hypothesis(id="H1", text="t"), run_id="run-001")

    res = G54MemoryLedgerWrittenGate().check(
        {"run_root": str(run_root), "run_id": "run-001", "memory_db": str(db)}
    )
    assert res.status == GateStatus.PASS


def test_block_when_artifacts_present_but_ledger_empty(tmp_path):
    run_root = _run_with_artifacts(tmp_path)
    db = tmp_path / "memory" / "ledger.db"
    ProjectMemoryStore(db)  # db exists but no rows for run-001

    res = G54MemoryLedgerWrittenGate().check(
        {"run_root": str(run_root), "run_id": "run-001", "memory_db": str(db)}
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_memory_db_missing_and_artifacts_present(tmp_path):
    run_root = _run_with_artifacts(tmp_path)
    res = G54MemoryLedgerWrittenGate().check(
        {
            "run_root": str(run_root),
            "run_id": "run-001",
            "memory_db": str(tmp_path / "memory" / "nonexistent.db"),
        }
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_skip_when_no_ledgerable_artifacts(tmp_path):
    run_root = tmp_path / "triggers" / "run-empty"
    run_root.mkdir(parents=True)
    res = G54MemoryLedgerWrittenGate().check(
        {"run_root": str(run_root), "run_id": "run-empty", "memory_db": str(tmp_path / "m.db")}
    )
    assert res.status == GateStatus.SKIP
