"""G3: drug names must resolve to canonical INN via RxNorm. Spec §7 G3 / E4."""
from __future__ import annotations

from typing import Any

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.rxnorm import RxNormIntegrator

from ..mechanical_gates import Gate, GateResult, GateStatus


class G3DrugNormalizationGate(Gate):
    name = "G3_drug_normalization"
    description = "Every drug name must resolve to a canonical generic via RxNorm."
    failure_mode_code = "E4"

    def __init__(self, rxnorm: RxNormIntegrator) -> None:
        self.rxnorm = rxnorm

    def check(self, claim: dict[str, Any]) -> GateResult:
        raise NotImplementedError("G3 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        drugs = claim.get("drugs", []) or []
        if not drugs:
            return GateResult(gate=self.name, status=GateStatus.SKIP, message="no drugs in claim")
        unresolved: list[str] = []
        resolutions: dict[str, str] = {}
        for d in drugs:
            try:
                rec = await self.rxnorm.cached_fetch(f"brand:{d}")
                resolutions[d] = rec.get("generic", "")
            except IntegratorError:
                unresolved.append(d)
        if unresolved:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                message=f"unresolved drug names: {unresolved}",
                evidence={"unresolved": unresolved, "resolutions": resolutions},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"resolved {len(drugs)} drugs",
            evidence={"resolutions": resolutions},
        )
