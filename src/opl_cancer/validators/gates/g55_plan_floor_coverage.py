"""G55: plan_floor_coverage — the LLM plan may expand, but never drop the floor.

D1/E1 / ADR-0034. The de-scripting conversion pattern: LLM judges, a gate
verifies the floor. When the keyword/threshold comorbidity router is replaced by
an LLM planner, the SAFETY part of those thresholds (the red-line
contraindication-mandated experts/tasks, backed by clinical_stop_rules.json /
drug_comorbidity_contraindications.json / G40) is extracted into this
deterministic floor gate. The LLM may EXPAND the team freely (generalization),
but if a red-line is present the mandated expert/task MUST be in the plan
(safety). Machine-verifiable: floor_required must be a subset of planned_experts.

Inputs (claim dict): planned_experts (list), floor_required (list).
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


class G55PlanFloorCoverageGate(Gate):
    """An LLM-composed plan must cover the deterministic red-line safety floor."""

    name = "G55_plan_floor_coverage"
    description = (
        "When an LLM planner composes the team, any red-line "
        "contraindication-mandated expert/task (the safety floor extracted from "
        "the comorbidity rules) MUST be present. The LLM may expand beyond the "
        "floor, never drop it. BLOCKS. Machine-verifiable (floor ⊆ plan)."
    )
    failure_mode_code = "D1-FLOOR-DROPPED"
    family_id = "safety-disclosure"

    def check(self, claim: dict[str, Any]) -> GateResult:
        floor = claim.get("floor_required")
        planned = claim.get("planned_experts")
        if not isinstance(floor, list) or not floor:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G55 SKIP — no red-line safety floor for this patient.")
        planned_set = {str(x).lower() for x in planned} if isinstance(planned, list) else set()
        missing = [str(x) for x in floor if str(x).lower() not in planned_set]
        if missing:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    f"G55 FAIL — the plan dropped red-line safety-floor expert(s)/task(s): "
                    f"{missing}. The LLM planner may expand the team freely but must never "
                    "drop a contraindication-mandated role. Add them to the plan."
                ),
                evidence={"missing": missing, "floor_required": floor},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=f"G55 OK — plan covers all {len(floor)} red-line floor item(s).",
            evidence={"floor_required": floor},
        )
