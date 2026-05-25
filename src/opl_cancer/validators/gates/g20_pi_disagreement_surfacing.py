"""G20: PI must surface Reviewer↔Executor disagreement. Spec §7 G20 / §6.5 PI-C3.

Failure mode PI-C3 — PI output silently hides disagreement: when
``reviewer.disagreement.confidence_delta > 0.4`` OR ``reviewer.audit_flag``
is non-empty, the patient-facing output MUST visibly mark the divergence
(otherwise the patient sees a falsely unified recommendation).

Regex match against the union of all PI prose fields, accepting any of:
  * "Reviewer ⟂ Executor"
  * "team 内部分歧"
  * "两个视角"
  * "**Reviewer 在这一点上分歧了**"
  * "Reviewer disagrees" / "second opinion differs"
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_DISAGREEMENT_MARKER = re.compile(
    r"(Reviewer\s*[⟂⊥|/]\s*Executor|"
    r"Reviewer\s+disagrees|second\s+opinion\s+differs|"
    r"team\s*内部分歧|两个视角|两种视角|"
    r"\*\*\s*Reviewer\s+在这一点上分歧了\s*\*\*|"
    r"Reviewer\s+在这一点上分歧了|"
    r"分歧已上浮)",
    re.IGNORECASE,
)

_PI_FIELDS = ("pi_delivery", "patient_brief", "patient_facing_summary", "patient_message")


def _walk_strings(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            out.extend(_walk_strings(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_walk_strings(v))
    return out


def _disagreement_present(claim: dict[str, Any], threshold: float) -> tuple[bool, dict[str, Any]]:
    reviewer = claim.get("reviewer") or {}
    delta = reviewer.get("disagreement", {}).get("confidence_delta")
    audit_flag = reviewer.get("audit_flag")
    delta_f: float | None
    try:
        delta_f = float(delta) if delta is not None else None
    except (TypeError, ValueError):
        delta_f = None
    triggered = bool(audit_flag) or (delta_f is not None and abs(delta_f) > threshold)
    return triggered, {"confidence_delta": delta_f, "audit_flag": audit_flag}


class G20PIDisagreementSurfacingGate(Gate):
    name = "G20_pi_disagreement_surfacing"
    description = "When Reviewer disagrees, PI prose MUST carry a visible disagreement marker."
    failure_mode_code = "PI-C3"

    def __init__(self, confidence_delta_threshold: float = 0.4) -> None:
        self.threshold = confidence_delta_threshold

    def check(self, claim: dict[str, Any]) -> GateResult:
        triggered, info = _disagreement_present(claim, self.threshold)
        if not triggered:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="reviewer disagreement below threshold and no audit_flag — no PI marker required",
                evidence=info,
            )
        pi_blobs: list[str] = []
        for key in _PI_FIELDS:
            sub = claim.get(key)
            if sub is not None:
                pi_blobs.extend(_walk_strings(sub))
        if not pi_blobs:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="reviewer disagreement present but no PI prose to inspect",
                evidence=info,
            )
        if any(_DISAGREEMENT_MARKER.search(b) for b in pi_blobs):
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="disagreement surfaced in PI prose",
                evidence=info,
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=True,
            message=(
                "reviewer disagreement triggered but PI prose does not surface it "
                f"(threshold={self.threshold}, info={info})"
            ),
            evidence=info,
        )
