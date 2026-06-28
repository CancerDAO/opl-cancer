"""G48: research_delta — a run must produce net-new knowledge vs the prior run.

A3 / ADR-0028 (research-team iteration). Every wave, gate and attestation in OPL
inspects the REPORT (anchored? tiered? safe?). None checks that RESEARCH
happened. A cold re-run that re-derives an identical brief passes everything —
the 'better report generator' failure the whole iteration exists to fix.

G48 reads the patient research ledger (A1) and compares this run to the prior
run on the same patient. A run shows positive research-delta if it did any of:
  * proposed a NEW direction (a hypothesis id not seen in any prior run),
  * KILLED a direction (a hypothesis status falsified/weakened/pruned this run),
  * recorded a REALITY outcome (A2 reconciliation against the patient's course),
  * resolved an outstanding question (an 'resolved_question' ledger record).

Block policy: **FLAG, not BLOCK** (block=False). A genuinely stable follow-up
should not exit non-zero — but a null-research run must be surfaced, never
shipped as if it were progress. First run (no prior) → SKIP (nothing to compare).

Inputs (claim dict): run_id, memory_db.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opl_cancer.memory.store import ProjectMemoryStore

from ..mechanical_gates import Gate, GateResult, GateStatus

_KILLED = {"falsified", "weakened", "pruned"}
_DELTA_RECORD_TYPES = {"outcome", "resolved_question"}


class G48ResearchDeltaGate(Gate):
    """A run must add knowledge (new/killed direction or a reality outcome)."""

    name = "G48_research_delta"
    description = (
        "Compares this run to the prior run on the same patient via the research "
        "ledger. FLAGs (does not block) a run with zero net-new knowledge: no new "
        "direction, no killed direction, no reality outcome, no resolved question. "
        "Reframes success from report-quality to research progress — the "
        "mechanical 'team, not essayist' check. First run → SKIP."
    )
    failure_mode_code = "A3-NULL-RESEARCH-RUN"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_id = str(claim.get("run_id") or "")
        db_raw = claim.get("memory_db")
        db = Path(db_raw) if db_raw else None
        if not run_id or db is None or not db.is_file():
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G48 SKIP — no ledger / run_id; nothing to compare (first run?).",
            )
        store = ProjectMemoryStore(db)

        cur_hyps = store.query_hypotheses(run_id=run_id)
        # Run attribution per hypothesis comes from the ledger row, not the
        # payload, so read it directly. Everything from a run OTHER than the
        # current one is "prior".
        prior_ids: set[str] = set()
        has_prior_run = False
        for rt_run, ids in _hyp_ids_by_run(store).items():
            if rt_run != run_id:
                has_prior_run = True
                prior_ids |= ids
        if not has_prior_run:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G48 SKIP — no prior run for this patient; nothing to compare.",
            )

        cur_ids = {h.id for h in cur_hyps}
        new_directions = sorted(cur_ids - prior_ids)
        killed = sorted({h.id for h in cur_hyps if h.status in _KILLED})
        delta_records = sum(
            store.ledger_count(run_id=run_id, record_type=rt) for rt in _DELTA_RECORD_TYPES
        )

        if new_directions or killed or delta_records:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    f"G48 OK — research-delta present: {len(new_directions)} new "
                    f"direction(s), {len(killed)} killed, {delta_records} reality/"
                    "resolution record(s). The run compounded."
                ),
                evidence={
                    "new_directions": new_directions[:20],
                    "killed": killed[:20],
                    "delta_records": delta_records,
                },
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=False,  # FLAG — a stable follow-up shouldn't exit non-zero.
            message=(
                "G48 FLAG — NULL research run: this run reproduced prior knowledge "
                "with no new direction, no killed direction, and no reality outcome. "
                "All safety gates may be green, but no RESEARCH happened. Either "
                "this is a legitimately stable follow-up (say so to the patient) or "
                "the run is acting as a report generator, not a research team."
            ),
            evidence={"run_id": run_id, "prior_direction_count": len(prior_ids)},
        )


def _hyp_ids_by_run(store: ProjectMemoryStore) -> dict[str, set[str]]:
    """Map run_id → set of hypothesis ids, read straight from the ledger."""
    out: dict[str, set[str]] = {}
    with store._conn() as conn:  # noqa: SLF001 — same package, deterministic read
        rows = conn.execute(
            "SELECT run_id, record_id FROM ledger WHERE record_type='hypothesis'"
        ).fetchall()
    for run_id, record_id in rows:
        out.setdefault(run_id or "", set()).add(record_id)
    return out
