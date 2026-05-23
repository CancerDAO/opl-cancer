"""Test G3 Drug-normalization gate."""
from typing import Any, cast

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.rxnorm import RxNormIntegrator
from opl_cancer.validators.gates.g3_drug_normalization import G3DrugNormalizationGate
from opl_cancer.validators.mechanical_gates import GateStatus


class _FakeRx:
    family = "F10"
    ttl_seconds = 60
    cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        if "tylenol" in key.lower():
            return {"brand": "Tylenol", "generic": "acetaminophen", "rxcui": "161"}
        raise IntegratorError("unknown")


async def test_g3_pass_when_drug_normalizes() -> None:
    gate = G3DrugNormalizationGate(rxnorm=cast(RxNormIntegrator, _FakeRx()))
    claim = {"drugs": ["Tylenol"]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.PASS
    assert r.evidence["resolutions"]["Tylenol"] == "acetaminophen"


async def test_g3_fail_when_drug_unknown() -> None:
    gate = G3DrugNormalizationGate(rxnorm=cast(RxNormIntegrator, _FakeRx()))
    claim = {"drugs": ["MadeUpDrugX"]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert "MadeUpDrugX" in r.evidence["unresolved"]


async def test_g3_skip_when_no_drugs() -> None:
    gate = G3DrugNormalizationGate(rxnorm=cast(RxNormIntegrator, _FakeRx()))
    r = await gate.check_async({})
    assert r.status == GateStatus.SKIP
