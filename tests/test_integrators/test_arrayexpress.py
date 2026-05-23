"""ArrayExpressIntegrator tests — F6 P3-T2."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.arrayexpress import ArrayExpressIntegrator
from opl_cancer.integrators.base import IntegratorError


_STUDY = {
    "accno": "E-MTAB-12345",
    "section": {
        "type": "Study",
        "attributes": [
            {"name": "Title", "value": "Bulk RNA-seq of NSCLC PDX models"},
            {"name": "Description", "value": "16 PDX, EGFR-mutant vs WT"},
            {"name": "Organism", "value": "Homo sapiens"},
            {"name": "Assays", "value": 16},
        ],
    },
}


@respx.mock
async def test_fetch_by_accession() -> None:
    respx.get(url__regex=r".*biostudies/api/v1/studies/E-MTAB-12345").mock(
        return_value=Response(200, json=_STUDY)
    )
    integ = ArrayExpressIntegrator(cache=None)
    rec = await integ.fetch("E-MTAB-12345")
    assert rec["accession"] == "E-MTAB-12345"
    assert "NSCLC" in rec["title"]
    assert rec["organism"] == "Homo sapiens"


@respx.mock
async def test_fetch_unknown_prefix_raises() -> None:
    integ = ArrayExpressIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("GSE12345")


@respx.mock
async def test_fetch_404_raises() -> None:
    respx.get(url__regex=r".*biostudies.*").mock(return_value=Response(404))
    integ = ArrayExpressIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("E-MTAB-9999999")


def test_arrayexpress_family_is_f6() -> None:
    integ = ArrayExpressIntegrator(cache=None)
    assert integ.family == "F6"
