"""G21 — Quantitative anchor required for Wave-3-evidenced claims.

Spec §17.5 P0 + founder-mode "real prediction, not labels" (PRD §17.3 + landing
docs/landing/founder_mode_against_cancer.md L22):

> "OPL gives quantitative prediction — pooled HR/OR/RR + 95% CI + p-value +
>  patient-projected scores + Cox / KM survival predictions + drug ranking
>  with quantified efficacy scores."

A claim that has Wave 3 evidence (a notebook output, a meta-analysis result,
or a patient-projection score) MUST surface numeric values in its delivery
text — not just a qualitative label like "WNT-high may affect ICI response."

This gate runs in two places:
- After patient_brief_rendering (Wave 5) — checks delivery markdown
- After pi_delivery (Wave 5) — checks Sid's conversational rewrite

Failure mode: F6 (real prediction collapsed to hypothesis label). New code
introduced in v1.3.0 EVAL panel feedback (Patient #1 P1-6).
"""
from __future__ import annotations

import re
from typing import Any

from opl_cancer.validators.mechanical_gates import Gate, GateResult, GateStatus


# A claim with Wave 3 evidence must contain at least one quantitative anchor.
# Anchors recognised:
#   1. Pooled effect-size with CI:    "HR 1.42 [95% CI 1.10–1.85]" / "OR 0.31 [0.18-0.54]"
#   2. Percentile / score:            "projected to the 87th percentile" / "投射在第 87 百分位"
#   3. Survival number:               "median OS 14.2 mo" / "median PFS 5.8 months"
#   4. p-value:                       "p = 0.003" / "p < 0.001"
#   5. Probability / hazard:          "12-month OS probability 0.48"
#   6. Cox β / log-rank χ²:           "Cox β = 0.71" / "log-rank χ² = 12.4"
_PATTERNS = [
    re.compile(r"\bHR\s*[=:]?\s*[0-9]+\.[0-9]+\s*\[?\s*95\s*%\s*CI", re.IGNORECASE),
    re.compile(r"\bOR\s*[=:]?\s*[0-9]+\.[0-9]+\s*\[?\s*95\s*%\s*CI", re.IGNORECASE),
    re.compile(r"\bRR\s*[=:]?\s*[0-9]+\.[0-9]+\s*\[?\s*95\s*%\s*CI", re.IGNORECASE),
    re.compile(r"\b(?:百分位|percentile)\s*(?:[0-9]+|第\s*[0-9]+)", re.IGNORECASE),
    re.compile(r"\bmedian\s+(?:OS|PFS|TTP|DFS)\s+[0-9]+\.?[0-9]*\s*(?:mo|months?)", re.IGNORECASE),
    re.compile(r"\b(?:中位|中位数)\s*(?:OS|PFS|TTP|DFS|生存期)\s*[0-9]+\.?[0-9]*\s*(?:月|months?)", re.IGNORECASE),
    re.compile(r"\bp\s*[<>=]\s*0\.[0-9]+"),
    re.compile(r"\b(?:probability|概率|prob)\s*[=:]?\s*0?\.[0-9]+"),
    re.compile(r"\b(?:Cox\s*β|Cox\s*beta|log-rank\s*χ²|log-rank\s*chi)", re.IGNORECASE),
    re.compile(r"\bIC50\s*[=:]?\s*[0-9]+\.?[0-9]*\s*(?:nM|μM|uM)", re.IGNORECASE),
    re.compile(r"\b[0-9]+\.?[0-9]*\s*(?:%|percent)\s*(?:ORR|response\s*rate|应答率|ORR)", re.IGNORECASE),
]


class G21QuantitativeAnchorGate(Gate):
    """Block Wave-3-evidenced claims that lack any quantitative anchor.

    A claim is "Wave 3-evidenced" if its `evidence` list contains an entry of
    type `dataset` or `meta_analysis` or `cox_model` or `km_curve` — i.e. the
    analysis pipeline produced a real numeric output that must surface to the
    patient.

    Qualitative claims (purely from literature without Wave 3 reanalysis) are
    not subject to this gate.
    """

    gate_id = "G21"
    description = "Quantitative-anchor required for Wave-3-evidenced claims"

    def evaluate(self, claim: dict[str, Any]) -> GateResult:
        evidence = claim.get("evidence", [])
        wave3_types = {"dataset", "meta_analysis", "cox_model", "km_curve", "projection", "n1_prediction"}
        has_wave3 = any(
            isinstance(e, dict) and str(e.get("type", "")).lower() in wave3_types
            for e in evidence
        )
        if not has_wave3:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.SKIP,
                detail="claim has no Wave-3 evidence; gate not applicable",
            )

        # Search delivery text + claim text + evidence quotes for any anchor.
        text_fields = [
            claim.get("claim", ""),
            claim.get("delivery_text", ""),
            claim.get("delivery_markdown", ""),
            claim.get("pi_prose", ""),
        ]
        haystack = " \n ".join(str(f) for f in text_fields if f)
        for e in evidence:
            if isinstance(e, dict):
                for k in ("quote", "summary", "result_text"):
                    v = e.get(k, "")
                    if v:
                        haystack += " \n " + str(v)

        for pat in _PATTERNS:
            if pat.search(haystack):
                return GateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.PASS,
                    detail="quantitative anchor present",
                )

        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.FAIL,
            block=True,
            detail=(
                "claim has Wave-3 evidence but delivery text contains no quantitative "
                "anchor (HR/OR/RR with CI, percentile projection, median survival, "
                "Cox β, p-value, IC50, ORR%). Rewrite delivery to surface the numbers — "
                "founder-mode: 'real prediction, not labels'. See "
                "docs/landing/founder_mode_against_cancer.md L22 + "
                "references/founder-mode-philosophy.md."
            ),
        )
