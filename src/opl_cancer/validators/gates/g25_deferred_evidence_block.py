"""G25: deferred-evidence BLOCK gate. v1.5 P0-5.

Failure mode F-NEW-1 (introduced v1.5): an evidence-critical claim is
declared "deferred / skipped / not run" but the run still produces a
patient-facing delivery. In v1.4 the PT-EXAMPLE-A run silently skipped
Wave 3 and shipped the package; Henry passed it because the format gates
accepted explicit "deferred" labels as compliant
(docs/ANTI_PATTERNS_v1.4.md AP-1, AP-2).

This gate fires on Wave-4 / delivery-stage claims. If a claim is tagged
``deferred=true`` OR contains marker phrases like ``[SKIPPED]`` /
``[NOT RUN]`` / ``"deferred to next wave"`` AND the run is at the
delivery stage (``claim.run_stage in {"wave4_validation",
"wave5_delivery"}``), the gate BLOCKS unless either:

  1. The claim is explicitly opt-in deferred by the patient (``claim.patient_optout``
     true with a rationale), OR
  2. The deferred analysis is non-critical (``claim.evidence_criticality !=
     "critical"``).

Otherwise: BLOCK with the specific deferred-evidence reason. The patient
brief / pi delivery must hold back the regimen recommendation that
depends on that evidence until the analysis actually runs.
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_DEFERRED_MARKERS = re.compile(
    r"(\[SKIPPED\]|\[NOT\s+RUN\]|\[DEFERRED\]|"
    r"deferred\s+to\s+next\s+wave|wave\s*3\s+skipped|"
    r"docker\s+unavailable[,;:]?\s*wave\s*3\s+skipped)",
    re.IGNORECASE,
)
_DELIVERY_STAGES = {"wave4_validation", "wave5_delivery", "delivery", "patient_brief"}


class G25DeferredEvidenceBlockGate(Gate):
    name = "G25_deferred_evidence_block"
    description = (
        "Block delivery when evidence-critical claim is marked deferred / "
        "skipped, unless explicit patient opt-out or non-critical."
    )
    failure_mode_code = "F-NEW-1"

    def check(self, claim: dict[str, Any]) -> GateResult:
        stage = (claim.get("run_stage") or "").lower()
        if stage and stage not in _DELIVERY_STAGES:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"non-delivery stage {stage!r}; no enforcement",
            )

        # Explicit per-claim deferred flag wins
        deferred_flag = bool(claim.get("deferred")) or bool(claim.get("skipped"))

        # Marker phrases anywhere in claim text / status
        text_fields = []
        for key in ("status", "verdict", "summary", "notes", "rationale"):
            v = claim.get(key)
            if isinstance(v, str):
                text_fields.append(v)
        joined_text = " ".join(text_fields)
        marker_hit = bool(_DEFERRED_MARKERS.search(joined_text))

        is_deferred = deferred_flag or marker_hit
        if not is_deferred:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="no deferred-evidence markers detected",
            )

        criticality = (claim.get("evidence_criticality") or "critical").lower()
        if criticality != "critical":
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    f"deferred but evidence_criticality={criticality!r}; "
                    "not blocking"
                ),
                evidence={"deferred": True, "criticality": criticality},
            )

        if claim.get("patient_optout") and claim.get("patient_optout_rationale"):
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="deferred under explicit patient opt-out",
                evidence={
                    "deferred": True,
                    "patient_optout": True,
                    "rationale": claim["patient_optout_rationale"],
                },
            )

        reason_bits = []
        if deferred_flag:
            reason_bits.append("explicit deferred/skipped flag set")
        if marker_hit:
            match = _DEFERRED_MARKERS.search(joined_text)
            reason_bits.append(
                f"deferred-marker phrase: {match.group(0)!r}"  # type: ignore[union-attr]
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=True,
            message=(
                "evidence-critical claim is deferred at delivery stage; "
                "regimen recommendation depending on it must be held back. "
                + "; ".join(reason_bits)
            ),
            evidence={
                "deferred": True,
                "criticality": criticality,
                "stage": stage,
                "reason": reason_bits,
            },
        )
