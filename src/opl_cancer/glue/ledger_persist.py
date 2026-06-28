"""A1 / ADR-0027 — persist a finished run into the patient research ledger.

This is the production caller that makes OPL's compounding spine real. The
audit's dominant finding was that every cross-run mechanism was orphaned —
``save_insight`` only called by ``withdraw``, hypotheses/tournament rounds
written to ``triggers/<run_id>/`` but never to ``memory/`` — so each run
started cold and could re-propose a direction it had already falsified.

``persist_run_to_ledger`` is invoked by the delivery runner at deliver/attest.
It reads the run's own artifacts and writes them to the patient ledger:

  * Wave-2 hypotheses (incl. ``status='falsified'``)  → ``save_hypothesis``
  * Wave-2 tournament rounds (if present)             → ``save_tournament_round``
  * delivered claims                                  → ``save_insight`` when the
    claim already carries full InsightCard provenance; otherwise preserved
    verbatim as a generic ``delivered_claim`` ledger row (we NEVER fabricate
    provenance to force an InsightCard).

Faithful + fail-soft: a malformed artifact is skipped, not invented around.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opl_cancer.memory.schemas import Hypothesis, InsightCard, TournamentRound
from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db

__all__ = ["persist_run_to_ledger"]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _hypotheses_from(wave2: Any) -> list[dict[str, Any]]:
    if isinstance(wave2, dict):
        for key in ("hypotheses", "top_k"):
            val = wave2.get(key)
            if isinstance(val, list):
                return [h for h in val if isinstance(h, dict)]
    if isinstance(wave2, list):
        return [h for h in wave2 if isinstance(h, dict)]
    return []


def _tournament_rounds_from(wave2: Any, run_root: Path) -> list[dict[str, Any]]:
    rounds: list[dict[str, Any]] = []
    if isinstance(wave2, dict) and isinstance(wave2.get("tournament_rounds"), list):
        rounds.extend(r for r in wave2["tournament_rounds"] if isinstance(r, dict))
    tdir = run_root / "tournament"
    if tdir.is_dir():
        for f in sorted(tdir.glob("*.json")):
            data = _load_json(f)
            if isinstance(data, dict) and data.get("round_id"):
                rounds.append(data)
            elif isinstance(data, list):
                rounds.extend(r for r in data if isinstance(r, dict) and r.get("round_id"))
    return rounds


def _claims_from(run_root: Path) -> list[dict[str, Any]]:
    for candidate in (run_root / "claims.json", run_root / "delivery" / "claims.json"):
        data = _load_json(candidate)
        if data is None:
            continue
        claims = data.get("claims", data) if isinstance(data, dict) else data
        if isinstance(claims, list):
            return [c for c in claims if isinstance(c, dict)]
    return []


def persist_run_to_ledger(
    run_root: Path, memory_db: Path | None = None
) -> dict[str, int]:
    """Persist run artifacts into the patient research ledger. Returns counts."""
    run_root = Path(run_root)
    db = Path(memory_db) if memory_db is not None else default_patient_memory_db(run_root)
    store = ProjectMemoryStore(db)
    run_id = run_root.name
    counts = {"hypotheses": 0, "tournament_rounds": 0, "insights": 0, "delivered_claims": 0}

    wave2 = _load_json(run_root / "wave2_hypotheses.json")
    for h in _hypotheses_from(wave2):
        try:
            hyp = Hypothesis.model_validate(h)
        except Exception:
            continue
        store.save_hypothesis(hyp, run_id=run_id)
        counts["hypotheses"] += 1

    for r in _tournament_rounds_from(wave2, run_root):
        try:
            rnd = TournamentRound.model_validate(r)
        except Exception:
            continue
        store.save_tournament_round(rnd, run_id=run_id)
        counts["tournament_rounds"] += 1

    for c in _claims_from(run_root):
        try:
            card = InsightCard.model_validate(c)
        except Exception:
            # Lighter claim without full provenance — keep it faithfully in the
            # ledger; never invent provenance to force an InsightCard.
            cid = str(c.get("claim_id") or c.get("id") or f"claim-{counts['delivered_claims']}")
            store.append_ledger("delivered_claim", cid, c, run_id=run_id)
            counts["delivered_claims"] += 1
            continue
        store.save_insight(card)
        counts["insights"] += 1

    return counts
