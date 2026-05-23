"""Test ClinVarIntegrator — variant clinical significance via NCBI E-utils."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.clinvar import ClinVarIntegrator


@respx.mock
async def test_fetch_variant_significance() -> None:
    respx.get(url__regex=r".*esearch\.fcgi.*db=clinvar.*").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get(url__regex=r".*esummary\.fcgi.*db=clinvar.*").mock(
        return_value=Response(200, json={
            "result": {"12345": {
                "title": "NM_005228.5(EGFR):c.2573T>G (p.L858R)",
                "clinical_significance": {"description": "Pathogenic"},
                "trait_set": [{"trait_name": "Non-small cell lung carcinoma"}],
            }, "uids": ["12345"]}
        })
    )
    i = ClinVarIntegrator(cache=None)
    r = await i.fetch("variant:EGFR L858R")
    assert "Pathogenic" in r["significance"]
    assert r["uid"] == "12345"


@respx.mock
async def test_fetch_raises_on_empty_search() -> None:
    respx.get(url__regex=r".*esearch.*db=clinvar.*").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": []}})
    )
    i = ClinVarIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("variant:NOPE NOPE")


def test_family_is_F4() -> None:
    assert ClinVarIntegrator(cache=None).family == "F4"
