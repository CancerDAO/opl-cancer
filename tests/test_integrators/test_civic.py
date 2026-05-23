"""Test CIViCIntegrator — clinical evidence grading via GraphQL."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.civic import CIViCIntegrator


@respx.mock
async def test_fetch_variant_evidence() -> None:
    respx.post("https://civicdb.org/api/graphql").mock(
        return_value=Response(200, json={
            "data": {"variants": {"nodes": [{
                "id": 12, "name": "L858R",
                "evidenceItems": {"nodes": [{
                    "id": 99, "evidenceLevel": "A", "evidenceDirection": "SUPPORTS",
                    "clinicalSignificance": "SENSITIVITYRESPONSE",
                    "drugs": [{"name": "Osimertinib"}],
                    "source": {"citationId": "31157963"},
                }]},
            }]}}})
    )
    i = CIViCIntegrator(cache=None)
    r = await i.fetch("EGFR:L858R")
    assert r["variant"] == "L858R"
    assert any(e["level"] == "A" for e in r["evidence_items"])


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.post("https://civicdb.org/api/graphql").mock(return_value=Response(500))
    i = CIViCIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("EGFR:T790M")


def test_family_is_F4() -> None:
    assert CIViCIntegrator(cache=None).family == "F4"
