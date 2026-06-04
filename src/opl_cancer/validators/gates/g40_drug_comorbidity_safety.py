"""G40: drug_comorbidity_safety — a recommended drug must be reconciled against
a colliding patient comorbidity.

v2.7.0 (ADR-0026 P1/P2 reasoning-quality layer, session 0d1017d4 cross-model
review). The driving incident: **Finding 5 (MAJOR)** — a bevacizumab-containing
backbone was recommended for a patient who had a **cardiac workup on file**, and
the report never reconciled the vasculotoxic agent with the cardiac history.
Bevacizumab carries a labelled CHF / arterial-thromboembolism risk; recommending
it for a patient with documented cardiac disease without saying a word about that
collision is exactly the kind of un-surfaced safety reasoning this gate stops.

Like every gate in this layer, G40 is **mechanical**. It does NOT decide whether
the drug is safe — the LLM (via prompt) makes that clinical call and records it in
``claim.comorbidity_safety``. G40 only checks that:

  1. for each drug in ``claim.drugs_mentioned``,
  2. that maps (via the curated FDA-label reference
     ``references/drug_comorbidity_contraindications.json``) to a labelled
     contraindication CLASS,
  3. whose ``match_comorbidities`` collide with a real comorbidity in the patient
     profile (``<patient_dir>/profile.json``),
  4. the loop is CLOSED in ``claim.comorbidity_safety`` — i.e.
     ``addressed == true`` AND the colliding comorbidity appears in
     ``comorbidities_considered``.

If a collision exists but the loop is not closed → **FAIL + BLOCK** (Fork A: this
is a SAFETY gate). If there are no drugs, or no resolvable patient profile, the
gate **SKIPs** (block=False) — it cannot judge.

The reference JSON is curated ESTABLISHED FDA-label fact (drug→contraindication
class), not LLM judgment and not a clinical keyword classifier
(no-hardcoded-keyword-list policy). ``match_comorbidities`` are plain
substrings used only to decide *which* comorbidity a drug must be reconciled
against; the reconciliation itself is the LLM's job.

Caller passes (via the delivery_gate_runner):
  * ``claim.drugs_mentioned``      — INN drug list the claim invokes.
  * ``claim.comorbidity_safety``   — the producer's reconciliation record.
  * ``claim.patient_dir``          — resolves ``profile.json`` comorbidities, OR
  * ``claim.profile``              — an already-loaded profile.json dict, OR
  * ``claim.comorbidities``        — an explicit comorbidity list (overrides).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# ── reference resolution ────────────────────────────────────────────────────


def _repo_root() -> Path:
    """Walk up to the OPL repo root (stable anchor for ``references/``).

    Mirrors glue/delivery_runner._repo_root: the repo root is the only place
    ``references/`` + ``knowledge/`` reliably coexist regardless of the
    patient-data layout the gate is invoked from.
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "references").is_dir() and (parent / "knowledge").is_dir():
            return parent
    # Fallback: src/opl_cancer/validators/gates/ → up 4 = repo root.
    return here.parents[4]


_REFERENCE_PATH = _repo_root() / "references" / "drug_comorbidity_contraindications.json"

# cached at module load; the curated reference is static FDA-label data.
_REFERENCE: dict[str, Any] | None = None


def _load_reference() -> dict[str, Any]:
    global _REFERENCE
    if _REFERENCE is None:
        try:
            data = json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        # drop the _meta block — only INN entries are drug records.
        _REFERENCE = {k: v for k, v in data.items() if not k.startswith("_")}
    return _REFERENCE


# ── patient comorbidity extraction ──────────────────────────────────────────


def _flatten_comorbidities(value: Any) -> list[str]:
    """Flatten a profile `comorbidities` value into a list of strings.

    Accepts a list of strings, a list of dicts (e.g. {"condition": "..."}),
    or a single string. Anything else is stringified defensively.
    """
    out: list[str] = []
    if value in (None, "", [], {}):
        return out
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        # dict of comorbidity records or a single record
        for v in value.values():
            out.extend(_flatten_comorbidities(v))
        # also include any plain string fields on a single record
        for k in ("condition", "name", "diagnosis", "label", "term"):
            if isinstance(value.get(k), str):
                out.append(value[k])
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for k in ("condition", "name", "diagnosis", "label", "term"):
                    if isinstance(item.get(k), str):
                        out.append(item[k])
                        break
                else:
                    out.extend(_flatten_comorbidities(item))
            else:
                out.append(str(item))
        return out
    return [str(value)]


def _resolve_comorbidities(claim: dict[str, Any]) -> tuple[list[str] | None, str]:
    """Return (comorbidities, source) or (None, reason-for-skip).

    Precedence: explicit claim.comorbidities > claim.profile > patient_dir.
    None means we could not resolve a profile at all (gate SKIPs).
    """
    if "comorbidities" in claim and claim["comorbidities"] not in (None, ""):
        return _flatten_comorbidities(claim["comorbidities"]), "claim.comorbidities"

    profile = claim.get("profile")
    if profile is None and claim.get("patient_dir"):
        pj = Path(claim["patient_dir"]) / "profile.json"
        if pj.is_file():
            try:
                profile = json.loads(pj.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                profile = None

    if isinstance(profile, dict):
        return _flatten_comorbidities(profile.get("comorbidities")), "profile.json"

    return None, "no patient profile (claim.profile / patient_dir/profile.json) resolvable"


# ── collision detection ─────────────────────────────────────────────────────


def _normalize(s: str) -> str:
    return s.strip().lower()


def _drug_record(reference: dict[str, Any], drug: str) -> dict[str, Any] | None:
    """Look up a drug record by INN, case-insensitively."""
    key = _normalize(drug)
    rec = reference.get(key)
    if isinstance(rec, dict):
        return rec
    for inn, candidate in reference.items():
        if not isinstance(candidate, dict):
            continue
        if _normalize(inn) == key or _normalize(str(candidate.get("inn", ""))) == key:
            return candidate
    return None


def _matching_comorbidities(
    match_tokens: list[str], patient_comorbidities: list[str]
) -> list[str]:
    """Return the patient comorbidity strings that collide with a class.

    A collision = a curated `match_comorbidities` token appears as a substring
    of a patient comorbidity (both lower-cased). Substring matching covers both
    ASCII (e.g. 'hypertension' in 'stage-1 hypertension') and CJK (e.g. '心脏'
    in '心脏功能检查异常').
    """
    hits: list[str] = []
    lowered = [(c, _normalize(c)) for c in patient_comorbidities]
    norm_tokens = [_normalize(t) for t in match_tokens if t]
    for original, low in lowered:
        if any(tok and tok in low for tok in norm_tokens):
            hits.append(original)
    return hits


def _loop_closed(
    safety: dict[str, Any] | None, colliding: list[str]
) -> tuple[bool, str]:
    """True if comorbidity_safety closes the loop for ALL colliding comorbidities.

    Closing the loop requires:
      * safety.addressed is explicitly true, AND
      * every colliding comorbidity appears (substring, case-insensitive) in
        safety.comorbidities_considered.
    """
    if not isinstance(safety, dict):
        return False, "claim.comorbidity_safety absent — collision never reconciled"
    if safety.get("addressed") is not True:
        return False, "comorbidity_safety.addressed is not true"
    considered = safety.get("comorbidities_considered") or []
    considered_norm = [_normalize(str(c)) for c in considered]
    unaddressed = []
    for c in colliding:
        cl = _normalize(c)
        if not any(cl in cc or cc in cl for cc in considered_norm if cc):
            unaddressed.append(c)
    if unaddressed:
        return False, (
            "comorbidities not in comorbidities_considered: " + ", ".join(unaddressed)
        )
    return True, ""


class G40DrugComorbiditySafetyGate(Gate):
    """A recommended drug must be reconciled against any colliding comorbidity."""

    name = "G40_drug_comorbidity_safety"
    description = (
        "For each INN in claim.drugs_mentioned that maps to a labelled FDA "
        "contraindication class colliding with a patient comorbidity "
        "(profile.json), claim.comorbidity_safety must close the loop "
        "(addressed==true AND the comorbidity in comorbidities_considered). "
        "Stops the 'bevacizumab recommended for a cardiac patient, collision "
        "never reconciled' failure mode (cross-model Finding 5). Reference is "
        "curated FDA-label fact, not LLM judgment."
    )
    failure_mode_code = "RQ-UNRECONCILED-DRUG-COMORBIDITY"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        drugs = claim.get("drugs_mentioned") or []
        drugs = [d for d in drugs if isinstance(d, str) and d.strip()]
        if not drugs:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G40 SKIP — no drugs_mentioned to check.",
            )

        comorbidities, source = _resolve_comorbidities(claim)
        if comorbidities is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"G40 SKIP — {source}.",
            )
        if not comorbidities:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    f"G40 SKIP — patient profile ({source}) lists no comorbidities; "
                    "nothing to reconcile against."
                ),
                evidence={"comorbidity_source": source},
            )

        reference = _load_reference()
        if not reference:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G40 SKIP — drug_comorbidity_contraindications.json reference "
                    "unavailable; cannot judge."
                ),
            )

        safety = claim.get("comorbidity_safety")
        violations: list[dict[str, Any]] = []
        collisions_checked = 0
        drugs_with_record = 0

        for drug in drugs:
            rec = _drug_record(reference, drug)
            if rec is None:
                continue  # drug not in curated reference → out of scope, cannot judge
            drugs_with_record += 1
            for cls in rec.get("contraindication_classes", []):
                match_tokens = cls.get("match_comorbidities", []) or []
                colliding = _matching_comorbidities(match_tokens, comorbidities)
                if not colliding:
                    continue
                collisions_checked += 1
                closed, reason = _loop_closed(safety, colliding)
                if not closed:
                    violations.append({
                        "drug": drug,
                        "inn": rec.get("inn", drug),
                        "contraindication_class": cls.get("class"),
                        "severity": cls.get("severity"),
                        "label_basis": cls.get("label_basis"),
                        "colliding_comorbidities": colliding,
                        "reason": reason,
                    })

        if violations:
            sample = "; ".join(
                f"{v['drug']} ({v['contraindication_class']}) vs "
                f"{v['colliding_comorbidities']} — {v['reason']}"
                for v in violations[:4]
            )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,  # Fork A: SAFETY gate hard-blocks.
                message=(
                    f"G40 FAIL — {len(violations)} drug/comorbidity collision(s) "
                    f"not reconciled in claim.comorbidity_safety. First: {sample}. "
                    "Record addressed=true and list the comorbidity in "
                    "comorbidities_considered (the LLM makes the clinical call; "
                    "this gate only requires it be made + surfaced)."
                ),
                evidence={
                    "violations": violations[:20],
                    "comorbidity_source": source,
                    "patient_comorbidities": comorbidities,
                    "drugs_checked": drugs,
                    "collisions_checked": collisions_checked,
                },
            )

        if drugs_with_record == 0:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    f"G40 SKIP — none of {drugs} are in the curated FDA-label "
                    "reference; cannot judge."
                ),
                evidence={"drugs_checked": drugs, "comorbidity_source": source},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G40 OK — {drugs_with_record} referenced drug(s) checked against "
                f"{len(comorbidities)} comorbidity(ies); {collisions_checked} "
                "collision(s) all reconciled in comorbidity_safety."
            ),
            evidence={
                "drugs_checked": drugs,
                "comorbidity_source": source,
                "collisions_checked": collisions_checked,
            },
        )
