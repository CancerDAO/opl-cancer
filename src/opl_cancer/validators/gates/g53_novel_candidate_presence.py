"""G53: novel_candidate_presence — surface an option the oncologist did not name.

D1/E1 / ADR-0034. OPL's reason to exist is producing a real option BEYOND the
treating team's pre-decided plan, steered by what THIS patient wants — not
re-narrating standard-of-care in nicer language. G53 requires the delivery to
contain >=1 candidate tagged ``not_in_treating_plan`` that is traceable + backed
(a real testability_path + a tier), OR an explicit honest statement that no
option beyond the current plan was found. Negative-guarded: a novel-LOOKING but
unbacked option (no testability_path/tier) does NOT satisfy the gate, so it
cannot be gamed by manufacturing a shiny-but-empty candidate. Machine-verifiable.

Inputs (claim dict): claims (list), no_option_beyond_plan (bool).
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def _is_backed_novel(c: dict[str, Any]) -> bool:
    if not c.get("not_in_treating_plan"):
        return False
    has_path = bool(c.get("testability_path")) or bool(c.get("evidence"))
    has_tier = bool(c.get("claim_layer") or c.get("tier"))
    return has_path and has_tier


class G53NovelCandidatePresenceGate(Gate):
    """Delivery must surface a backed not-in-plan candidate, or honestly state none."""

    name = "G53_novel_candidate_presence"
    description = (
        "The run must surface >=1 candidate the treating team did NOT name "
        "(not_in_treating_plan, with a real testability_path + tier), OR honestly "
        "state no option beyond the current plan was found. Negative-guarded: an "
        "unbacked novel-looking option does not satisfy it. Operationalizes "
        "outcome-backward problem selection; BLOCKS. Machine-verifiable."
    )
    failure_mode_code = "D1-NO-NOVEL-OPTION"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        claims = claim.get("claims")
        if not isinstance(claims, list):
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G53 SKIP — no claims to evaluate.")
        backed = [c for c in claims if isinstance(c, dict) and _is_backed_novel(c)]
        if backed:
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message=f"G53 OK — {len(backed)} backed not-in-treating-plan candidate(s) surfaced.",
                evidence={"novel_candidate_ids": [c.get("claim_id") for c in backed][:10]},
            )
        if claim.get("no_option_beyond_plan") is True:
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message="G53 OK — run honestly states no option beyond the current plan was found.",
            )
        # Distinguish 'nothing novel at all' from 'novel-looking but unbacked'.
        unbacked = [c for c in claims if isinstance(c, dict) and c.get("not_in_treating_plan")]
        why = (
            "a not_in_treating_plan candidate was offered but lacks a testability_path + tier "
            "(negative guard — novelty theater is not a real option)"
            if unbacked else
            "the run only re-narrated the treating plan and offered no option beyond it"
        )
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                f"G53 FAIL — {why}. Surface at least one backed candidate the oncologist "
                "did not name (with a real testability_path + tier), or state honestly "
                "that none was found (no_option_beyond_plan=true)."
            ),
            evidence={"unbacked_novel": len(unbacked)},
        )
