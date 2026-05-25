"""G4: every dose must declare unit + frequency. Spec §7 G4 / §6.5 A4.

Failure mode A4 — "计量单位混淆 / dose unit ambiguity": e.g. "give 10 cefepime"
or "1 mg/kg" without dosing interval (qd / bid / q3w …). G4 walks every dose
field on the claim and BLOCKs if any dose is missing a recognised unit OR a
recognised frequency token.

Recognised units (case-insensitive): mg, mcg, µg, g, mg/kg, mg·kg⁻¹, mg/m²,
mg·m⁻², IU, U, mL, mEq, ng/mL, ng·mL⁻¹.
Recognised frequencies: qd, bid, tid, qid, q3w, q21d, q4w, q28d, q2w, q14d,
qw, q1w, q8h, q12h, prn, stat, 每日, 每周, 每三周, 每两周.
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_UNIT_RE = re.compile(
    r"(?<![A-Za-z])("
    r"mg/kg|mg·kg⁻¹|mg/m²|mg·m⁻²|mg/m2|mg·m\^-2|"
    r"mcg|µg|ug|mg|g|ng/mL|ng·mL⁻¹|"
    r"IU|U|mL|mEq"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)
_FREQ_RE = re.compile(
    r"\b(qd|bid|tid|qid|q3w|q21d|q4w|q28d|q2w|q14d|qw|q1w|q8h|q12h|q24h|"
    r"prn|stat|po|iv)\b|每日|每天|每周|每三周|每两周|每月|每四周",
    re.IGNORECASE,
)


def _iter_doses(claim: dict[str, Any]) -> list[tuple[str, str]]:
    """Yield (field_path, dose_str) for every dose-bearing field."""
    out: list[tuple[str, str]] = []
    doses = claim.get("doses") or []
    if isinstance(doses, list):
        for i, d in enumerate(doses):
            if isinstance(d, dict):
                txt = d.get("text") or d.get("dose") or ""
                if txt:
                    out.append((f"doses[{i}]", str(txt)))
            elif isinstance(d, str):
                out.append((f"doses[{i}]", d))
    # also scan symptom_plan[].dose & treatment_plan[].dose
    for plan_key in ("symptom_plan", "treatment_plan", "regimens"):
        plan = claim.get(plan_key) or []
        if isinstance(plan, list):
            for i, p in enumerate(plan):
                if not isinstance(p, dict):
                    continue
                dose_txt = p.get("dose") or p.get("dosing") or ""
                if dose_txt:
                    out.append((f"{plan_key}[{i}].dose", str(dose_txt)))
    return out


class G4DoseUnitDeclaredGate(Gate):
    name = "G4_dose_unit_declared"
    description = "Every dose must declare an explicit unit AND a dosing frequency."
    failure_mode_code = "A4"

    def check(self, claim: dict[str, Any]) -> GateResult:
        doses = _iter_doses(claim)
        if not doses:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no doses in claim"
            )
        offenders: list[dict[str, str]] = []
        for path, text in doses:
            has_unit = bool(_UNIT_RE.search(text))
            has_freq = bool(_FREQ_RE.search(text))
            if not (has_unit and has_freq):
                offenders.append(
                    {
                        "field": path,
                        "text": text[:120],
                        "missing": ", ".join(
                            x for x, ok in (("unit", has_unit), ("frequency", has_freq)) if not ok
                        ),
                    }
                )
        if offenders:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"{len(offenders)} dose(s) missing unit or frequency",
                evidence={"offenders": offenders},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"all {len(doses)} dose(s) carry unit + frequency",
        )
