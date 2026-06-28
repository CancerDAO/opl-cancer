"""G45: world_unknown_comparator — speculative candidates need a fair SoC bar.

B1 / ADR-0029 (research-team iteration). The false-hope firewall. OPL v2 added
machinery to surface world-UNKNOWN candidates (target-synergy / undrugged-target
designs) to the patient — a genuine capability, but it shipped them with an Elo
number and a testability path and NO fair comparator. To a desperate late-line
patient an Elo rating next to a novel idea reads as absolute strength, while the
best real (world-KNOWN) option for their setting goes unstated. That is the exact
"gain that evaporates against a properly tuned baseline" — here, false hope.

G45 makes the comparator non-optional: any candidate flagged
``world_unknown_candidate`` must carry a ``world_known_comparator`` naming the
best world-known option for the same setting (so the candidate is read against a
real alternative, not in isolation). This is a fully machine-verifiable fact
(field present + ``best_world_known_option`` non-empty), so it BLOCKS — safety,
not quality.

The gate never judges WHICH option is best (that is the LLM's clinical call,
recorded in the field); it only enforces that the comparator was stated.

Field consumed (schemas/claim.v2.schema.json):
    world_known_comparator: {best_world_known_option, expected_pfs_months?,
        expected_os_months?, orr?, hr?, ci?, pmid?, human_efficacy_data_for_candidate?}
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def _is_world_unknown_candidate(claim: dict[str, Any]) -> bool:
    if claim.get("world_unknown_candidate") is True:
        return True
    # also fire on the v2 generation strategies that produce world-unknown ideas
    strat = str(claim.get("generation_strategy", ""))
    return strat in {"target_synergy_emergent", "undrugged_target_design"}


class G45WorldUnknownComparatorGate(Gate):
    """A world-unknown candidate must carry a fair world-known comparator."""

    name = "G45_world_unknown_comparator"
    description = (
        "Every world-unknown / speculative candidate surfaced to the patient must "
        "carry a world_known_comparator naming the best real (world-known) option "
        "for the same setting, so a novel idea is never read in isolation as if it "
        "were validated. Machine-verifiable; BLOCKS (false-hope firewall). The LLM "
        "decides which option is best; the gate only enforces it was stated."
    )
    failure_mode_code = "B1-NO-COMPARATOR"
    family_id = "safety-disclosure"

    def check(self, claim: dict[str, Any]) -> GateResult:
        if not _is_world_unknown_candidate(claim):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G45 SKIP — not a world-unknown candidate.",
            )
        comp = claim.get("world_known_comparator")
        best = comp.get("best_world_known_option") if isinstance(comp, dict) else None
        if not isinstance(comp, dict) or not (isinstance(best, str) and best.strip()):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G45 FAIL — world-unknown candidate "
                    f"{claim.get('claim_id', '?')!r} has no world_known_comparator "
                    "with a best_world_known_option. A speculative candidate must be "
                    "shown next to the best real option for this setting (false-hope "
                    "firewall) — an Elo number alone reads as validated strength."
                ),
                evidence={"claim_id": claim.get("claim_id"), "comparator": comp},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                "G45 OK — world-unknown candidate carries a fair comparator: "
                f"{best!r}."
            ),
            evidence={
                "claim_id": claim.get("claim_id"),
                "best_world_known_option": best,
                "human_efficacy_data_for_candidate": comp.get(
                    "human_efficacy_data_for_candidate"
                ),
            },
        )
