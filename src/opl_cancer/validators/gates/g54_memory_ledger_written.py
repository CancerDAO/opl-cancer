"""G54: memory_ledger_written — the run must persist what it learned.

A1 / ADR-0027 (research-team iteration). OPL's signature structural failure
(the audit's dominant finding) was that it terminated at delivery and reset to
zero every run: ``ProjectMemoryStore.save_insight`` was only ever called by the
``withdraw`` command, ``ingest_prior_runs`` was orphaned, and the ``memory/``
layout advertised in SKILL.md was a Potemkin ledger. Net effect: a returning
late-line patient's already-falsified directions vanished between runs, so OPL
could re-propose a hope it had already killed — a direct false-hope hazard.

G54 makes the compounding spine *mechanically enforced*: if a run produced
research artifacts worth persisting (hypotheses / a delivered brief) but wrote
ZERO rows to the patient research ledger for this run_id, delivery BLOCKS. This
is a fully **machine-verifiable fact** (artifacts on disk vs ledger row count),
not a judgement — exactly the kind of thing a no-LLM gate should enforce.

Block policy: BLOCK (block=True). Compounding is the property that separates a
research TEAM from a one-shot report generator; a run that does not compound is
not the service OPL promises.

Inputs (claim dict):
    run_root   : the ``triggers/<run_id>/`` directory (artifacts live here)
    run_id     : the run identifier (falls back to ``run_root`` dir name)
    memory_db  : path to the patient research-ledger SQLite DB
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# Artifacts whose presence means the run did research worth persisting.
_LEDGERABLE_ARTIFACTS = (
    "wave2_hypotheses.json",
    "delivery/patient_brief.md",
    "delivery/patient_brief.html",
)


def _artifacts_present(run_root: Path) -> list[str]:
    return [name for name in _LEDGERABLE_ARTIFACTS if (run_root / name).is_file()]


def _count_ledger_rows(db: Path, run_id: str) -> int:
    """Count ledger rows for this run without mutating the DB.

    Read-only on purpose: we do NOT instantiate ProjectMemoryStore here because
    its constructor would create an empty DB + schema as a side effect, masking
    a genuinely-missing ledger. A missing DB must surface as 'not written'.
    """
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM ledger WHERE run_id=?", (run_id,)
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


class G54MemoryLedgerWrittenGate(Gate):
    """A run that produced research artifacts must have written the ledger."""

    name = "G54_memory_ledger_written"
    description = (
        "If a run produced research artifacts (hypotheses / a delivered brief) "
        "but wrote zero rows to the patient research ledger for this run_id, the "
        "run did not compound — the next run starts cold and can re-propose a "
        "falsified direction. Machine-verifiable (artifacts vs ledger rows); "
        "BLOCKS delivery. The mechanical guarantee that OPL is a team, not a "
        "one-shot report generator."
    )
    failure_mode_code = "A1-NO-COMPOUNDING"
    family_id = "provenance"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root_raw = claim.get("run_root")
        if not run_root_raw:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G54 SKIP — no run_root provided; nothing to verify.",
            )
        run_root = Path(run_root_raw)
        run_id = str(claim.get("run_id") or run_root.name)

        present = _artifacts_present(run_root)
        if not present:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G54 SKIP — run produced no ledgerable research artifacts "
                    "(no hypotheses / no delivered brief) yet; nothing to persist."
                ),
                evidence={"run_id": run_id},
            )

        db_raw = claim.get("memory_db")
        db = Path(db_raw) if db_raw else None
        if db is None or not db.is_file():
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G54 FAIL — run produced research artifacts "
                    f"({', '.join(present)}) but the patient research ledger DB "
                    f"is missing ({db}). The run did not compound; deliver/attest "
                    "must persist hypotheses, tournament rounds and delivered "
                    "claims to the ledger before delivery."
                ),
                evidence={"run_id": run_id, "artifacts": present, "memory_db": str(db)},
            )

        try:
            rows = _count_ledger_rows(db, run_id)
        except sqlite3.Error as exc:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G54 FAIL — research ledger unreadable ({exc}); cannot "
                    "verify the run compounded. Fail-closed."
                ),
                evidence={"run_id": run_id, "memory_db": str(db)},
            )

        if rows == 0:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G54 FAIL — run produced research artifacts "
                    f"({', '.join(present)}) but wrote ZERO rows to the research "
                    f"ledger for run_id={run_id}. The run did not compound: the "
                    "next run would start cold and could re-propose a falsified "
                    "direction. Persist the run's hypotheses / tournament rounds / "
                    "delivered claims at deliver/attest."
                ),
                evidence={"run_id": run_id, "artifacts": present, "ledger_rows": 0},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G54 OK — run {run_id} persisted {rows} ledger row(s); the run "
                "compounds into patient memory."
            ),
            evidence={"run_id": run_id, "ledger_rows": rows},
        )
