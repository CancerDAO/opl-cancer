"""A2 / ADR-0028 — reality-outcome loop.

The single missing primitive no per-slice audit proposed: a channel through which
the patient's ACTUAL clinical course grades OPL's prior predictions. Today OPL's
only 'validation' (Wave 4) scores hypotheses against more literature/datasets —
circular. This module scores them against reality.

Flow (host-agent reasons; Python persists — harness-split):
  1. ``load_prior_predictions`` pulls the team's prior hypotheses (and forecasts,
     once C2 lands) from the research ledger.
  2. The host agent reads the new clinical datum from ``inbox/`` (a scan, marker,
     RECIST read, toxicity) and scores each prior prediction against it, emitting
     outcome records (see prompts/tasks/outcome_reconciliation.md).
  3. ``persist_outcomes`` writes those records to the ledger, keyed by run, so the
     team's real track record compounds — and so G48 (research_delta) sees that
     reality told the team something this run.

This is deliberately NOT a fresh clinical analysis (that would ignore the prior
predictions); it is a verdict on what the team already said.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opl_cancer.memory.store import ProjectMemoryStore

__all__ = ["load_prior_predictions", "persist_outcomes"]


def load_prior_predictions(memory_db: Path) -> dict[str, list[dict[str, Any]]]:
    """Return the team's prior predictions for the host to score against reality.

    Hypotheses carry their forecast fields once C2 (predict-before-you-look) lands;
    until then ``forecasts`` mirrors the hypotheses that carry a prior_expectation.
    """
    db = Path(memory_db)
    if not db.is_file():
        return {"hypotheses": [], "forecasts": []}
    store = ProjectMemoryStore(db)
    hyps = [h.model_dump(mode="json") for h in store.query_hypotheses()]
    forecasts = [h for h in hyps if h.get("prior_expectation")]
    return {"hypotheses": hyps, "forecasts": forecasts}


def persist_outcomes(
    memory_db: Path, run_id: str, outcomes: list[dict[str, Any]]
) -> int:
    """Persist host-produced reality-outcome records to the ledger. Returns count.

    Each record scores ONE prior prediction against a real clinical datum:
    {id, hypothesis_id?, pre_registered_direction?, real_world_datum,
     real_world_verdict, team_was_right}. We never invent a verdict — only what
     the host derived from the patient's actual course is stored.
    """
    store = ProjectMemoryStore(memory_db)
    n = 0
    for i, o in enumerate(outcomes):
        if not isinstance(o, dict):
            continue
        rec_id = str(o.get("id") or o.get("hypothesis_id") or f"outcome-{i}")
        store.append_ledger(
            "outcome",
            rec_id,
            o,
            run_id=run_id,
            status=str(o.get("real_world_verdict") or ""),
        )
        n += 1
    return n
