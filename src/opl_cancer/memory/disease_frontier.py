"""D4 / ADR-0037 — re-aim the learning loop at the disease frontier.

The audit's finding: OPL's only cross-run learning loop (evolution/) was being
extracted OUT of the patient product and, even present, learned about
OPL-the-software (system-design proposals for the next DIFFERENT patient), not
about THIS patient or the disease. A research team's institutional memory is
about the SCIENCE.

This builds the re-aimed digest cleanly from the compounding spine — the research
ledger (A1) + reality outcomes (A2) — so the learning loop's subject is the
patient's disease frontier:

  * killed_directions  — falsified hypotheses (don't re-propose; Darwin log)
  * reality_verdicts   — what the patient's ACTUAL course said about predictions
  * systematic_gaps    — recurring failure-pile root causes
  * open_frontier      — active hypotheses not yet reality-scored (chase these)

It deliberately does NOT import or modify the mid-extraction ``evolution/``
engine (whether that engine stays in the patient path or is extracted is the
founder's call — PRD §9 open-Q#3). This is the verifiable substance the re-aimed
loop consumes once that decision lands; it keeps the no-auto-apply posture (it
only *reports* a digest — it proposes nothing automatically).
"""
from __future__ import annotations

from .store import ProjectMemoryStore


def build_disease_frontier_digest(
    store: ProjectMemoryStore, run_id: str | None = None
) -> dict[str, object]:
    """Re-aimed learning digest about the patient's disease — built from reality."""
    killed = [
        {"id": h.id, "text": h.text}
        for h in store.query_hypotheses(status="falsified")
    ]
    killed_ids = {h["id"] for h in killed}
    outcomes = store.ledger_rows(record_type="outcome", run_id=run_id)
    scored_ids = {o.get("hypothesis_id") for o in outcomes}
    open_frontier = [
        {"id": h.id, "text": h.text}
        for h in store.query_hypotheses(status="active")
        if h.id not in killed_ids and h.id not in scored_ids
    ]
    return {
        "aimed_at": "patient_disease_frontier",  # NOT OPL-software self-improvement
        "killed_directions": killed,
        "reality_verdicts": outcomes,
        "systematic_gaps": store.ledger_rows(record_type="failure_pile", run_id=run_id),
        "open_frontier": open_frontier,
        "auto_apply": False,  # report-only; human double-signoff posture preserved
    }


__all__ = ["build_disease_frontier_digest"]
