"""G9: any retracted DOI in evidence must block (spec §7 G9 / D1)."""
from __future__ import annotations

from typing import Any

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.retractiondb import RetractionDBIntegrator

from ..mechanical_gates import Gate, GateResult, GateStatus


class G9RetractionCheckGate(Gate):
    name = "G9_retraction_check"
    description = "Any DOI referenced must not be retracted."
    failure_mode_code = "D1"

    def __init__(self, retractiondb: RetractionDBIntegrator) -> None:
        self.retractiondb = retractiondb

    def check(self, claim: dict[str, Any]) -> GateResult:
        raise NotImplementedError("G9 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        dois = [e["doi"] for e in claim.get("evidence", []) if e.get("doi")]
        if not dois:
            return GateResult(gate=self.name, status=GateStatus.SKIP, message="no DOIs to check")
        retracted: list[dict[str, Any]] = []
        for doi in dois:
            try:
                rec = await self.retractiondb.cached_fetch(f"DOI:{doi}")
                if rec.get("retracted"):
                    retracted.append(rec)
            except IntegratorError as e:
                # G11 spirit — if check itself fails, raise outward via FAIL+block
                return GateResult(
                    gate=self.name,
                    status=GateStatus.FAIL,
                    block=True,
                    message=f"retraction check transport failed: {e}",
                )
        if retracted:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"retracted citations found: {len(retracted)}",
                evidence={"retracted": retracted},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS, message=f"checked {len(dois)} DOIs"
        )
