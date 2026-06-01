"""v2.7.0 ADR-0026 — delivery-integrity gate runner (the wiring that fires the gates).

CLI wiring: the ``cli.py`` ``deliver`` / ``render`` / ``audit`` / ``attest`` / ``go``
commands all route through this module's ``run_delivery_gates`` to mechanically
*sweep* a delivery package against the G34-G43 gates and emit a verdict
(``DELIVERY_ATTESTATION.json``). This is the *gate-sweep wiring*; it differs from the
sibling ``delivery_runner.py``, which is the *atomic delivery transaction* that
actually writes the briefs + Henry audit (all-or-nothing, with rollback).

The root cause of session 0d1017d4 was NOT missing gates — it was that the gates
were never on the path the agent ran. This module is the connective tissue: a
single ``run_delivery_gates`` that the CLI ``deliver`` / ``render`` / ``audit`` /
``attest`` / ``go`` commands all route through, so a delivery is mechanically
checked for:

  * G34 delivery_attestation   — the brief is backed by a real run (manifest +
                                  provenance journal + real Henry audit).
  * G37 service_completeness   — the full planned team & warranted waves ran
                                  (no silent 20→4 collapse, no under-delivery).
  * G35 clinical_fact_provenance — case_text asserts no un-sourced clinical value
                                  (no fabricated creatinine).
  * G36 pmid_topic_relevance + G1 pmid_existence + G2 quote_match — every cited
                                  PMID exists, matches its quote, and is on-topic
                                  (no real-but-wrong-paper citations). These need
                                  live integrators; when none are supplied the
                                  verdict records ``citation_gates: not_run`` —
                                  an HONEST note, never a silent pass.

``run_delivery_gates`` returns a verdict dict and writes ``DELIVERY_ATTESTATION.json``
next to the briefs. ``ok=False`` means the CLI must refuse delivery (exit ≠ 0).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.validators.gates import (
    G34DeliveryAttestationGate,
    G35ClinicalFactProvenanceGate,
    G36PMIDTopicRelevanceGate,
    G37ServiceCompletenessGate,
    G39BiomarkerContingencyGate,
    G40DrugComorbiditySafetyGate,
    G41SoCCompletenessGate,
    G42TierDisciplineGate,
    G43EpistemicSymmetryGate,
)
from opl_cancer.validators.mechanical_gates import Gate, GateResult, GateStatus

ATTESTATION_FILE = "DELIVERY_ATTESTATION.json"


def _patient_dir_for(run_root: Path) -> Path | None:
    """run_root = <patient>/triggers/<run_id> → patient dir is two levels up."""
    if run_root.parent.name == "triggers":
        return run_root.parent.parent
    return None


def _record(results: list[dict[str, Any]], blocked: list[str], r: GateResult) -> None:
    results.append({
        "gate": r.gate, "status": r.status.value, "block": r.block,
        "message": r.message, "evidence": r.evidence,
    })
    if r.block and r.status is GateStatus.FAIL:
        blocked.append(r.gate)


async def _run_citation_gates(
    claims: list[dict[str, Any]], pubmed: Any, paperqa: Any | None,
) -> list[GateResult]:
    """Await the async citation gates over every claim that carries PMID evidence."""
    from opl_cancer.validators.gates import G1PMIDExistenceGate, G2PMIDQuoteMatchGate

    out: list[GateResult] = []
    g36 = G36PMIDTopicRelevanceGate(pubmed)
    g1 = G1PMIDExistenceGate(pubmed)
    g2 = G2PMIDQuoteMatchGate(paperqa) if paperqa is not None else None
    for c in claims:
        if not [e for e in c.get("evidence", []) if e.get("type") == "pmid"]:
            continue
        out.append(await g1.check_async(c))
        out.append(await g36.check_async(c))
        if g2 is not None:
            out.append(await g2.check_async(c))
    return out


def run_delivery_gates(
    *,
    run_root: Path,
    out_dir: Path | None = None,
    claims: list[dict[str, Any]] | None = None,
    pubmed: Any | None = None,
    paperqa: Any | None = None,
    brief_path: str | None = None,
    write_attestation: bool = True,
) -> dict[str, Any]:
    """Run the delivery-integrity gates. Returns a verdict dict.

    ``ok`` is False iff any hard-block gate FAILed — the caller must then refuse
    delivery. The verdict is also persisted to ``<out_dir>/DELIVERY_ATTESTATION.json``.
    """
    run_root = Path(run_root)
    out_dir = Path(out_dir) if out_dir is not None else run_root / "delivery"
    patient_dir = _patient_dir_for(run_root)

    results: list[dict[str, Any]] = []
    blocked: list[str] = []
    notes: list[str] = []

    # ── structural gates (sync, no network) ──
    _record(results, blocked, G34DeliveryAttestationGate().check({
        "run_root": str(run_root), "out_dir": str(out_dir), "brief_path": brief_path,
    }))
    _record(results, blocked, G37ServiceCompletenessGate().check({"run_root": str(run_root)}))

    # G35 only when there is a case_text to scan (else SKIP is implicit).
    if patient_dir is not None and (patient_dir / "case_text.md").is_file():
        _record(results, blocked, G35ClinicalFactProvenanceGate().check({
            "patient_dir": str(patient_dir),
        }))
    else:
        notes.append("G35 clinical_fact_provenance: no case_text.md to scan at this layer.")

    # ── citation gates (async, need live integrators) ──
    if claims is None:
        claims = _load_claims(run_root, out_dir)
    pmid_claims = [c for c in claims if any(
        e.get("type") == "pmid" for e in c.get("evidence", [])
    )]
    if pmid_claims:
        if pubmed is not None:
            for r in asyncio.run(_run_citation_gates(pmid_claims, pubmed, paperqa)):
                _record(results, blocked, r)
        else:
            notes.append(
                f"citation_gates (G1/G2/G36): NOT RUN — {len(pmid_claims)} claim(s) cite "
                "PMIDs but no PubMed/PaperQA2 integrator was supplied. This is an honest "
                "gap, not a pass; supply integrators (live path) to verify citations."
            )
            # A medical brief must not ship
            # unverified citations. With PMID-bearing claims and no integrator we
            # CANNOT verify them, so the delivery is BLOCKED (ok=False), not a
            # silent pass. Record a sentinel gate name in `blocked` so it surfaces
            # in verdict["blocked_by"] exactly like a hard-block gate failure.
            blocked.append("citation_gates_not_run")

    # ── reasoning-quality gates (sync, per-claim) — G39/G40/G42 hard-block,
    #    G41/G43 + G42-adjacency warn (Fork A). These check structured fields the
    #    claim producer emits; a claim missing the field SKIPs (not a block). ──
    reasoning_gates: list[Gate] = [
        G39BiomarkerContingencyGate(),
        G40DrugComorbiditySafetyGate(),
        G41SoCCompletenessGate(),
        G42TierDisciplineGate(),
        G43EpistemicSymmetryGate(),
    ]
    warned: list[str] = []
    for c in claims:
        # G40 needs the patient profile to resolve comorbidities.
        claim_in = dict(c)
        if patient_dir is not None and "patient_dir" not in claim_in:
            claim_in["patient_dir"] = str(patient_dir)
        for g in reasoning_gates:
            r = g.check(claim_in)
            if r.status is GateStatus.SKIP:
                continue
            _record(results, blocked, r)
            # FAIL with block=False is a warn — surface it without failing delivery.
            if r.status is GateStatus.FAIL and not r.block:
                warned.append(f"{r.gate} on {c.get('claim_id', '?')}: {r.message}")
    if warned:
        notes.append(f"reasoning-quality warnings (non-blocking): {warned}")

    verdict = {
        "ok": not blocked,
        "blocked_by": blocked,
        "gate_results": results,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_root": str(run_root),
    }
    if write_attestation:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / ATTESTATION_FILE).write_text(
            json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return verdict


def _load_claims(run_root: Path, out_dir: Path) -> list[dict[str, Any]]:
    for candidate in (run_root / "claims.json", out_dir / "claims.json"):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
            claims = data.get("claims", data) if isinstance(data, dict) else data
            return [c for c in claims if isinstance(c, dict)] if isinstance(claims, list) else []
    return []


__all__ = ["run_delivery_gates", "ATTESTATION_FILE"]
