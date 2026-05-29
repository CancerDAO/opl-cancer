"""G41: soc_completeness — the producer must record a standard-of-care
completeness check, and no SoC item may be left silently dropped.

v2.7.0 (ADR-0026 P1/P2, session 0d1017d4 — KRAS-G12C/MSS mCRC cross-model
review). The driving incident: Finding 6 (MAJOR) — the brief was missing
patient-specific standard-of-care that a tumour board would routinely raise:

  * re-biopsy / ctDNA urgency because the molecular profile rested on
    3-year-old archival tissue (clonal evolution likely),
  * local consolidative therapy for lung oligoprogression,
  * recurrence-pattern characterization.

No gate caught it because nothing required the producer to *enumerate* the
SoC options warranted for the patient's setting and mark which were addressed.
A silently-dropped SoC option is an UNDER-delivery failure: the brief looks
complete but a board would flag the gap.

G41 is a **no-LLM, mechanical** gate. It does NOT decide which SoC items are
warranted — that is a clinical judgment the LLM makes (via the claim_audit /
brief-assembly prompt) and records in the structured ``soc_checklist`` field.
G41 only enforces that:

  1. the producer RECORDED a SoC-completeness check at all (field present); and
  2. every recorded item is internally coherent — an item flagged
     ``status=="missing"`` surfaces LOUDLY (it is a warranted SoC element the
     brief did not cover); an item ``"na"`` (not applicable to this patient)
     or ``"missing"`` must carry a non-empty ``note`` explaining why.

Block policy (Fork A — founder decision): G41 is a QUALITY gate, so it is
**WARN, not block** (block=False). A 'missing' item FAILs the gate (so it is
recorded in the attestation and surfaced loudly in evidence) but does NOT fail
delivery. Safety gates block; quality gates warn.

UNIVERSAL late-line floor items a tumour board would expect a SoC checklist to
have *considered* (recorded as addressed / na, not silently absent) — kept here
purely as documentation, NEVER as a hardcoded clinical decision the gate makes:

  * tissue-recency / re-biopsy when the molecular profile rests on aged tissue,
  * liquid biopsy (ctDNA) as a less-invasive alternative / for clonal-evolution
    capture,
  * local consolidative therapy for oligoprogressive disease,
  * recurrence-pattern / progression-pattern characterization.

The gate does NOT check for these strings — listing them would be exactly the
hardcoded-clinical-judgment anti-pattern this iteration exists to avoid. The
producer prompt is responsible for ensuring the checklist is populated and
covers the patient's setting; G41 only verifies the recorded checklist is
present and coherent.

Field consumed (schemas/claim.v2.schema.json):
    soc_checklist: [{item, status: addressed|missing|na, note}]

The checklist is read from the claim itself, or — for a run-level SoC check —
from ``claim["run"]["soc_checklist"]`` / ``claim["soc_checklist"]``. Absent ⇒
SKIP (block=False): the gate cannot judge completeness it was never given.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# Statuses the schema permits. An item with an out-of-vocabulary status is
# itself a coherence violation (the producer recorded something the gate cannot
# interpret), surfaced as a malformed item rather than silently ignored.
_VALID_STATUSES = {"addressed", "missing", "na"}
# Statuses that REQUIRE a non-empty note (per the schema: why missing / why na).
_NOTE_REQUIRED_STATUSES = {"missing", "na"}


def _extract_checklist(claim: dict[str, Any]) -> Any:
    """Pull soc_checklist from the claim, or from a run-level wrapper.

    Returns the raw value (any type) or None if the field is wholly absent, so
    the caller can distinguish 'not recorded' (SKIP) from 'recorded empty'.
    """
    if "soc_checklist" in claim:
        return claim.get("soc_checklist")
    run = claim.get("run")
    if isinstance(run, dict) and "soc_checklist" in run:
        return run.get("soc_checklist")
    return None


class G41SoCCompletenessGate(Gate):
    """Producer must record a SoC-completeness check; no item silently dropped."""

    name = "G41_soc_completeness"
    description = (
        "Mechanically verifies the producer RECORDED a standard-of-care "
        "completeness check (soc_checklist) and that it is coherent: any item "
        "marked status=='missing' is a warranted SoC element the brief did not "
        "cover and is surfaced loudly; 'missing'/'na' items must carry a note. "
        "WARN-only (quality gate, block=False). Catches the under-delivery "
        "failure mode (KRAS-G12C/MSS Finding 6: re-biopsy/ctDNA urgency on "
        "3-yr-old tissue, local consolidative therapy for oligoprogression, "
        "recurrence-pattern characterization silently dropped). The LLM decides "
        "WHICH items are warranted; this gate never re-makes that clinical call."
    )
    failure_mode_code = "Q6-SOC-UNDERDELIVERED"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        checklist = _extract_checklist(claim)

        # Field wholly absent → the producer never recorded a SoC check.
        # SKIP (block=False): the gate cannot judge what it was not given.
        # The producer prompt is responsible for populating this.
        if checklist is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G41 SKIP — SoC completeness not recorded (no soc_checklist). "
                    "The producer prompt must enumerate the standard-of-care items "
                    "warranted for this patient's setting and mark each "
                    "addressed/missing/na."
                ),
            )

        # Present but not a list → malformed; treat as recorded-but-incoherent.
        if not isinstance(checklist, list):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,
                message=(
                    "G41 WARN — soc_checklist present but is not a list "
                    f"(got {type(checklist).__name__}); cannot verify completeness."
                ),
                evidence={"soc_checklist_type": type(checklist).__name__},
            )

        # Present and an empty list → recorded but with zero items. That is a
        # coherent statement of 'I considered SoC and listed nothing', which is
        # almost certainly under-delivery for a late-line brief. WARN.
        if len(checklist) == 0:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,
                message=(
                    "G41 WARN — soc_checklist is empty. A late-line brief should "
                    "enumerate the standard-of-care options it considered (even to "
                    "mark them 'na' with a reason)."
                ),
                evidence={"item_count": 0},
            )

        missing_items: list[dict[str, Any]] = []
        note_missing_items: list[dict[str, Any]] = []
        malformed_items: list[dict[str, Any]] = []
        addressed = 0
        na = 0

        for idx, raw in enumerate(checklist):
            if not isinstance(raw, dict):
                malformed_items.append({"index": idx, "reason": "item is not an object",
                                        "value": str(raw)[:120]})
                continue
            item_name = raw.get("item")
            status = raw.get("status")
            note = (raw.get("note") or "").strip() if isinstance(raw.get("note"), str) else ""

            if not isinstance(item_name, str) or not item_name.strip():
                malformed_items.append({"index": idx, "reason": "missing/empty 'item'",
                                        "status": status})
                continue
            if status not in _VALID_STATUSES:
                malformed_items.append({"index": idx, "item": item_name,
                                        "reason": f"status {status!r} not in {sorted(_VALID_STATUSES)}"})
                continue

            if status == "missing":
                entry = {"item": item_name, "note": note}
                missing_items.append(entry)
                if not note:
                    note_missing_items.append({"item": item_name, "status": status,
                                               "reason": "status=='missing' requires a note"})
            elif status == "na":
                na += 1
                if not note:
                    note_missing_items.append({"item": item_name, "status": status,
                                               "reason": "status=='na' requires a note"})
            else:  # addressed
                addressed += 1

        item_count = len(checklist)

        # Any 'missing' item, any item missing its required note, or any
        # malformed item → WARN (FAIL with block=False). Surface LOUDLY in
        # evidence so it lands in the attestation.
        if missing_items or note_missing_items or malformed_items:
            parts: list[str] = []
            if missing_items:
                names = ", ".join(m["item"] for m in missing_items[:6])
                parts.append(f"{len(missing_items)} SoC item(s) left MISSING: {names}")
            if note_missing_items:
                parts.append(f"{len(note_missing_items)} item(s) lack the required note")
            if malformed_items:
                parts.append(f"{len(malformed_items)} malformed item(s)")
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,  # Fork A: quality gate → WARN, never blocks delivery.
                message=(
                    "G41 WARN — standard-of-care completeness gap recorded by the "
                    "producer: " + "; ".join(parts) + ". These are warranted SoC "
                    "options the brief did not cover (under-delivery). A tumour "
                    "board would expect them addressed or explicitly marked na with "
                    "a reason. (Quality gate — does NOT block delivery.)"
                ),
                evidence={
                    "item_count": item_count,
                    "addressed": addressed,
                    "na": na,
                    "missing_items": missing_items[:20],
                    "items_missing_note": note_missing_items[:20],
                    "malformed_items": malformed_items[:20],
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G41 OK — SoC completeness recorded: {item_count} item(s), all "
                f"addressed or marked na with a reason ({addressed} addressed, "
                f"{na} na). No SoC option silently dropped."
            ),
            evidence={"item_count": item_count, "addressed": addressed, "na": na},
        )
