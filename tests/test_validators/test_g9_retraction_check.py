"""Test G9 Retraction-check gate."""
from typing import Any, cast

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.retractiondb import RetractionDBIntegrator
from opl_cancer.validators.gates.g9_retraction_check import G9RetractionCheckGate
from opl_cancer.validators.mechanical_gates import GateStatus


class _FakeRet:
    family = "F1"
    ttl_seconds = 60
    cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        doi = key.replace("DOI:", "")
        if doi == "10.bad/x":
            return {"doi": doi, "retracted": True, "retraction_doi": "10.bad/notice"}
        return {"doi": doi, "retracted": False, "retraction_doi": None}


class _FailingRet:
    family = "F1"
    ttl_seconds = 60
    cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        raise IntegratorError("transport failed")


async def test_g9_pass_when_no_retractions() -> None:
    gate = G9RetractionCheckGate(retractiondb=cast(RetractionDBIntegrator, _FakeRet()))
    claim = {"evidence": [{"type": "pmid", "id": "1", "doi": "10.ok/x", "quote": "q"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.PASS


async def test_g9_fail_block_when_retracted() -> None:
    gate = G9RetractionCheckGate(retractiondb=cast(RetractionDBIntegrator, _FakeRet()))
    claim = {"evidence": [{"type": "pmid", "id": "1", "doi": "10.bad/x", "quote": "q"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


async def test_g9_skip_when_no_dois() -> None:
    gate = G9RetractionCheckGate(retractiondb=cast(RetractionDBIntegrator, _FakeRet()))
    claim = {"evidence": [{"type": "guideline", "id": "NCCN", "quote": "q"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.SKIP


async def test_g9_fail_block_on_transport_error() -> None:
    gate = G9RetractionCheckGate(retractiondb=cast(RetractionDBIntegrator, _FailingRet()))
    claim = {"evidence": [{"type": "pmid", "id": "1", "doi": "10.x/y", "quote": "q"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "transport" in r.message
