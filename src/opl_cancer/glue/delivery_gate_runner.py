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
import re
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
from opl_cancer.validators.fakery_sniffer import (
    scan_artifact,
    scan_brief_artifact,
)
from opl_cancer.validators.mechanical_gates import Gate, GateResult, GateStatus

ATTESTATION_FILE = "DELIVERY_ATTESTATION.json"

# Brief filename shapes the renderer emits (md + html). Used by every
# brief-scanning helper so they stay in lockstep.
_BRIEF_GLOBS = ("*brief.md", "*brief.html", "patient_brief.html")
# PMID / treatment-content signals in brief PROSE (not structured side-files).
_PMID_PROSE_RE = re.compile(r"\[?PMID\s*:?\s*(\d{4,9})\]?", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
# Drug / treatment-content signals: a dose unit, an efficacy %, or an explicit
# recommendation verb next to a drug-shaped token. Conservative — we only need
# to know the brief carries *clinical/treatment* content (so it MUST be gated).
_DOSE_UNIT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|µg|ug|mcg|g|mL|ml|IU|U)(?:\s*/\s*(?:m2|m²|kg|day|d))?",
    re.IGNORECASE,
)
_EFFICACY_PCT_RE = re.compile(
    r"\b(?:ORR|DCR|PFS|OS|缓解率|有效率|客观缓解率?|无进展生存|总生存)\b[^\n]{0,24}?\d"
    r"|\d{1,3}(?:\.\d+)?\s*%[^\n]{0,12}?(?:response|缓解|生存|survival|control|控制)",
    re.IGNORECASE,
)


def _iter_brief_files(out_dir: Path) -> list[Path]:
    """All delivered brief files (md + html) under ``out_dir`` (deduped)."""
    if not out_dir.is_dir():
        return []
    seen: set[Path] = set()
    out: list[Path] = []
    for pat in _BRIEF_GLOBS:
        for p in sorted(out_dir.glob(pat)):
            rp = p.resolve()
            if rp not in seen and p.is_file():
                seen.add(rp)
                out.append(p)
    return out


def _delivery_has_brief(out_dir: Path) -> bool:
    return bool(_iter_brief_files(out_dir))


def _run_fakery_gate(out_dir: Path, *, claims: list[dict[str, Any]]) -> GateResult:
    """P0.3b — fakery sniffer over the FINAL rendered briefs.

    Placeholder language (TODO / 待填充 / <insert PMID>) is a HARD block — a
    delivered brief that still admits it is unfinished must never ship.
    Confident-but-unanchored efficacy %/drug+dose signals are recorded as
    WARN (flag-for-review) here; they only hard-block via P0.3c when the brief
    has no gated claims at all (avoids false positives on properly-gated prose).
    """
    briefs = _iter_brief_files(out_dir)
    if not briefs:
        return GateResult(
            gate="fakery_sniffer_delivery",
            status=GateStatus.SKIP,
            message="fakery_sniffer_delivery SKIP — no delivered brief to scan.",
        )
    gated_pmids = {
        str(e.get("id"))
        for c in claims
        for e in c.get("evidence", []) if e.get("type") == "pmid" and e.get("id")
    }
    placeholder_hits: list[dict[str, Any]] = []
    unanchored_hits: list[dict[str, Any]] = []
    for bp in briefs:
        for f in scan_artifact(bp):
            placeholder_hits.append({"file": bp.name, "line": f.line_number,
                                     "pattern": f.pattern, "excerpt": f.excerpt[:160]})
        for f in scan_brief_artifact(bp, gated_pmids=gated_pmids):
            unanchored_hits.append({"file": bp.name, "line": f.line_number,
                                    "kind": f.pattern, "excerpt": f.excerpt[:160]})

    if placeholder_hits:
        return GateResult(
            gate="fakery_sniffer_delivery",
            status=GateStatus.FAIL,
            block=True,
            message=(
                f"fakery_sniffer_delivery FAIL — {len(placeholder_hits)} placeholder / "
                "unfinished-scaffold marker(s) in the delivered brief; a brief that "
                "still contains TODO / 待填充 / <insert PMID> must not ship."
            ),
            evidence={"placeholder_hits": placeholder_hits[:20],
                      "unanchored_signals": unanchored_hits[:20]},
        )
    if unanchored_hits:
        return GateResult(
            gate="fakery_sniffer_delivery",
            status=GateStatus.FAIL,
            block=False,  # WARN — flag for review (conservative, avoid false +)
            message=(
                f"fakery_sniffer_delivery WARN — {len(unanchored_hits)} confident-but-"
                "unanchored clinical signal(s) (efficacy %/drug+dose) in the brief that "
                "carry no [[src:]]/[PMID:]/tier anchor. Flagged for review (non-blocking "
                "here; hard-blocks via P0.3c when the brief has no gated claims)."
            ),
            evidence={"unanchored_signals": unanchored_hits[:20]},
        )
    return GateResult(
        gate="fakery_sniffer_delivery",
        status=GateStatus.PASS,
        message=f"fakery_sniffer_delivery OK — {len(briefs)} brief(s) clean.",
    )


def _scan_brief_clinical_content(out_dir: Path) -> dict[str, Any]:
    """P0.3c — does the rendered brief carry clinical/treatment content?

    Returns a dict with ``has_content`` (drug+dose, efficacy numbers, or PMIDs
    in prose found), the candidate ``brief_pmids`` extracted from prose, and the
    first clinical line (for surfacing). Empty/absent brief ⇒ has_content False.
    """
    briefs = _iter_brief_files(out_dir)
    brief_pmids: set[str] = set()
    has_content = False
    first_clinical_line = ""
    files_scanned: list[str] = []
    for bp in briefs:
        files_scanned.append(bp.name)
        raw = bp.read_text(encoding="utf-8", errors="replace")
        if bp.suffix.lower() in (".html", ".htm"):
            raw = _HTML_TAG_RE.sub(" ", raw)
        brief_pmids.update(_PMID_PROSE_RE.findall(raw))
        for line in raw.splitlines():
            s = line.strip()
            if not s or s.startswith("[BACKGROUND]"):
                continue
            if _DOSE_UNIT_RE.search(s) or _EFFICACY_PCT_RE.search(s) or _PMID_PROSE_RE.search(s):
                has_content = True
                if not first_clinical_line:
                    first_clinical_line = s[:200]
    return {
        "has_content": has_content,
        "brief_pmids": sorted(brief_pmids),
        "first_clinical_line": first_clinical_line,
        "files_scanned": files_scanned,
    }


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

    # Load claims early — the fakery gate (P0.3b) and the brief-vs-claims
    # cross-check (P0.3c) both need to know whether any gated claim exists.
    if claims is None:
        claims = _load_claims(run_root, out_dir)

    # ── structural gates (sync, no network) ──
    _record(results, blocked, G34DeliveryAttestationGate().check({
        "run_root": str(run_root), "out_dir": str(out_dir), "brief_path": brief_path,
    }))
    _record(results, blocked, G37ServiceCompletenessGate().check({"run_root": str(run_root)}))

    # G35 — scan case_text.md AND (v2.10 P0.3a) the delivered briefs. A
    # fabricated clinical value can live ONLY in the patient-facing brief with no
    # case_text behind it, so G35 must see the delivery dir even when there is no
    # case_text.md at this layer.
    g35_in: dict[str, Any] = {"delivery_dir": str(out_dir)}
    if patient_dir is not None:
        g35_in["patient_dir"] = str(patient_dir)
    has_case_text = patient_dir is not None and (patient_dir / "case_text.md").is_file()
    has_brief = _delivery_has_brief(out_dir)
    if has_case_text or has_brief:
        _record(results, blocked, G35ClinicalFactProvenanceGate().check(g35_in))
    else:
        notes.append(
            "G35 clinical_fact_provenance: no case_text.md and no delivered brief "
            "to scan at this layer."
        )

    # ── v2.10 P0.3b — run the fakery sniffer on the FINAL rendered briefs ──
    # The wave runners sniff their own intermediate artifacts; nothing sniffed
    # the delivered package. A fabricated brief (placeholder OR confident-but-
    # unanchored efficacy %/drug+dose) must be caught here. Placeholder language
    # (TODO / 待填充 / <insert PMID>) is a HARD block; unanchored efficacy/dose
    # signals are flag-for-review unless the brief has no gated claims at all (in
    # which case P0.3c below already hard-blocks the whole delivery).
    _record(results, blocked, _run_fakery_gate(out_dir, claims=claims))

    # ── v2.10 P0.3c — brief-has-content-but-no-gated-claims hard block ──
    # The red-team hole: when claims.json is empty/missing the citation gates
    # below were skipped entirely, so a brief that recommends a drug + dose +
    # invented efficacy with NO claims.json shipped ok=True. Close it: if the
    # rendered brief carries clinical / treatment content (drug names, efficacy
    # numbers, PMIDs in prose) but there are no gated claims to back it, BLOCK.
    # Where the brief exposes candidate PMIDs in prose, surface them so they can
    # be run through the citation gates rather than silently passing.
    brief_content = _scan_brief_clinical_content(out_dir)
    if brief_content["has_content"] and not claims:
        _record(results, blocked, GateResult(
            gate="brief_has_claims_but_no_gated_claims",
            status=GateStatus.FAIL,
            block=True,
            message=(
                "delivery BLOCKED — the rendered brief asserts clinical/treatment "
                "content (drug names / efficacy numbers / PMIDs in prose) but there "
                "is NO gated claims.json behind it. Every clinical claim in the "
                "brief must originate from a gated, provenance-anchored claim; a "
                "brief with no claims record is unverifiable and may be fabricated."
            ),
            evidence=brief_content,
        ))
        # Promote any candidate PMIDs found in the brief into synthetic claims so
        # the citation gates below at least attempt to verify what the brief
        # cites (when an integrator is supplied).
        for pmid in sorted(brief_content.get("brief_pmids", [])):
            claims.append({
                "claim_id": f"brief_pmid:{pmid}",
                "claim_text": brief_content.get("first_clinical_line", ""),
                "evidence": [{"type": "pmid", "id": pmid}],
                "_source": "brief_text_extracted",
            })

    # ── citation gates (async, need live integrators) ──
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
