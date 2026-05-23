"""G1: every PMID in claim.evidence must exist on PubMed (spec §7 G1 / A1 fabrication)."""
from __future__ import annotations

from typing import Any

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.pubmed import PubMedIntegrator

from ..mechanical_gates import Gate, GateResult, GateStatus


class G1PMIDExistenceGate(Gate):
    name = "G1_pmid_existence"
    description = "Every PMID cited must be verifiable on PubMed."
    failure_mode_code = "A1"

    def __init__(self, pubmed: PubMedIntegrator) -> None:
        self.pubmed = pubmed

    def check(self, claim: dict[str, Any]) -> GateResult:  # sync wrapper raises
        raise NotImplementedError("G1 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        pmids = [e["id"] for e in claim.get("evidence", []) if e.get("type") == "pmid"]
        if not pmids:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no PMID evidence to check"
            )
        missing: list[str] = []
        for pmid in pmids:
            try:
                await self.pubmed.cached_fetch(f"PMID:{pmid}")
            except IntegratorError:
                missing.append(pmid)
        if missing:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"PMIDs not found on PubMed: {missing}",
                evidence={"missing_pmids": missing},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS, message=f"verified {len(pmids)} PMIDs"
        )
