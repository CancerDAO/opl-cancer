"""Test G1 PMID-existence gate."""
from typing import Any, cast

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.pubmed import PubMedIntegrator
from opl_cancer.validators.gates.g1_pmid_existence import G1PMIDExistenceGate
from opl_cancer.validators.mechanical_gates import GateStatus


class _FakePubMed:
    family = "F1"
    ttl_seconds = 60

    def __init__(self, *, known_pmids: set[str]) -> None:
        self.known = known_pmids
        self.cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        pmid = key.replace("PMID:", "")
        if pmid in self.known:
            return {"pmid": pmid, "title": "ok"}
        raise IntegratorError(f"unknown PMID {pmid}")


async def test_g1_passes_for_existing_pmid() -> None:
    gate = G1PMIDExistenceGate(
        pubmed=cast(PubMedIntegrator, _FakePubMed(known_pmids={"38219045"})),
    )
    claim = {"evidence": [{"type": "pmid", "id": "38219045", "quote": "x"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.PASS


async def test_g1_fails_and_blocks_for_fake_pmid() -> None:
    gate = G1PMIDExistenceGate(
        pubmed=cast(PubMedIntegrator, _FakePubMed(known_pmids=set())),
    )
    claim = {"evidence": [{"type": "pmid", "id": "99999999", "quote": "fake"}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "99999999" in r.message


async def test_g1_skips_for_non_pmid_evidence_only() -> None:
    gate = G1PMIDExistenceGate(
        pubmed=cast(PubMedIntegrator, _FakePubMed(known_pmids=set())),
    )
    claim = {"evidence": [{"type": "guideline", "id": "NCCN-HCC-D", "quote": "..."}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.SKIP
