"""G46: soc_baseline_quantified — ranked options need a tuned SoC baseline.

B1 / ADR-0029 (research-team iteration). "Tune your baselines until it hurts."
The graveyard of ML — and of clinical decision-support — is full of gains that
evaporate against a properly tuned baseline. The SMTB benchmark showed a
framework can HURT decision-restraint/concordance vs a tuned baseline. So when
OPL ranks treatment options for a patient, it must state honestly the best
realistic standard-of-care option for THIS setting — with a quantitative anchor
(HR/CI or expected PFS/OS) and a PMID — and make every option beat THAT, not a
strawman or nothing.

G46 BLOCKS a treatment-line claim that ranks options without a populated,
quantified ``soc_baseline``. Machine-verifiable: options present ⇒ soc_baseline
must carry best_option + ≥1 quantitative anchor + a source. The gate does NOT
decide what the baseline IS (clinical judgment, recorded by the LLM); it
enforces that a quantified baseline was stated.

Field consumed (schemas/claim.v2.schema.json):
    soc_baseline: {best_option, expected_pfs_months?, expected_os_months?,
                   orr?, hr?, ci?, pmid?, patients_own_current_plan?}
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_QUANT_KEYS = ("hr", "expected_pfs_months", "expected_os_months", "orr")


def _ranks_options(claim: dict[str, Any]) -> bool:
    opts = claim.get("options")
    if isinstance(opts, list) and len(opts) >= 1:
        return True
    return str(claim.get("claim_type", "")) == "treatment_line" and bool(claim.get("options"))


class G46SoCBaselineQuantifiedGate(Gate):
    """A treatment-line claim that ranks options must carry a quantified SoC baseline."""

    name = "G46_soc_baseline_quantified"
    description = (
        "When OPL ranks treatment options, it must state the best realistic "
        "standard-of-care option for this setting with a quantitative anchor "
        "(HR/CI or expected PFS/OS) and a source, so every option is measured "
        "against a tuned baseline rather than a strawman. Machine-verifiable; "
        "BLOCKS. The LLM decides the baseline; the gate enforces it is quantified."
    )
    failure_mode_code = "B1-NO-TUNED-BASELINE"
    family_id = "statistical-validity"

    def check(self, claim: dict[str, Any]) -> GateResult:
        if not _ranks_options(claim):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G46 SKIP — claim does not rank treatment options.",
            )
        base = claim.get("soc_baseline")
        if not isinstance(base, dict):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G46 FAIL — treatment-line claim "
                    f"{claim.get('claim_id', '?')!r} ranks options but states no "
                    "soc_baseline. Name the best realistic standard-of-care option "
                    "and make every option beat it (tuned baseline, not a strawman)."
                ),
                evidence={"claim_id": claim.get("claim_id")},
            )
        best = base.get("best_option")
        has_quant = any(base.get(k) not in (None, "", 0) for k in _QUANT_KEYS)
        has_source = bool(base.get("pmid") or base.get("nct") or base.get("guideline"))
        problems = []
        if not (isinstance(best, str) and best.strip()):
            problems.append("missing best_option")
        if not has_quant:
            problems.append(f"no quantitative anchor (need one of {list(_QUANT_KEYS)})")
        if not has_source:
            problems.append("no source (pmid/nct/guideline)")
        if problems:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G46 FAIL — soc_baseline present but not quantified: "
                    + "; ".join(problems)
                    + ". A baseline without a number cannot be beaten honestly."
                ),
                evidence={"claim_id": claim.get("claim_id"), "soc_baseline": base},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G46 OK — quantified SoC baseline stated: {best!r}; options are "
                "measured against a tuned baseline."
            ),
            evidence={"claim_id": claim.get("claim_id"), "best_option": best},
        )
