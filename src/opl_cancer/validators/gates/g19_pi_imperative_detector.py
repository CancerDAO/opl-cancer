"""G19: imperative detector applied to PI / patient-brief prose. Spec §7 G19 / §6.5 PI-C1.

Failure mode PI-C1 — PI (Patient Interface) prose emits command-form
recommendations directly to the patient. G19 reuses G7's English + 中文
imperative regexes but scopes them to the PI delivery fields:
  * `pi_delivery.*` (any string)
  * `patient_brief.*`
  * `patient_facing_summary`

Same evidence + risk-caveat exception as G7: imperative phrasing is OK
if the sentence also carries an evidence token (PMID/NCT/URL) and a risk
keyword (may / risk / 可能 / 风险 …).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus
from .g7_imperative_detector import (
    _EN_IMPERATIVE,
    _EVIDENCE_TOKEN,
    _RISK_KEYWORD,
    _SENT_SPLIT,
    _ZH_IMPERATIVE,
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


class G19PIImperativeDetectorGate(Gate):
    name = "G19_pi_imperative_detector"
    description = "Block imperatives in PI / patient-brief prose without PMID + risk caveat."
    failure_mode_code = "PI-C1"

    def check(self, claim: dict[str, Any]) -> GateResult:
        pi_blobs: list[str] = []
        for key in _PI_FIELDS:
            sub = claim.get(key)
            if sub is not None:
                pi_blobs.extend(_walk_strings(sub))
        if not pi_blobs:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no PI prose fields on claim"
            )
        offenders: list[str] = []
        for blob in pi_blobs:
            for sent in _SENT_SPLIT.split(blob):
                s = sent.strip()
                if not s:
                    continue
                if not (_EN_IMPERATIVE.search(s) or _ZH_IMPERATIVE.search(s)):
                    continue
                has_evidence = bool(_EVIDENCE_TOKEN.search(s))
                has_risk = bool(_RISK_KEYWORD.search(s))
                if has_evidence and has_risk:
                    continue
                offenders.append(s[:200])
        if offenders:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"PI prose contains {len(offenders)} imperative sentence(s) "
                    "without PMID+risk caveat"
                ),
                evidence={"offending_sentences": offenders},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"PI prose clean across {len(pi_blobs)} string field(s)",
        )


# Re-export the imperative regex constants for testability of G19 scoping.
__all__ = [
    "G19PIImperativeDetectorGate",
    "_EN_IMPERATIVE",
    "_ZH_IMPERATIVE",
    "_EVIDENCE_TOKEN",
    "_RISK_KEYWORD",
]


# silence unused-import lint when modules are re-bound only for downstream use
_ = (_EN_IMPERATIVE, _ZH_IMPERATIVE, _EVIDENCE_TOKEN, _RISK_KEYWORD, _SENT_SPLIT, re)
