"""Test cBioPortalIntegrator — cohort variant frequency lookup."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.cbioportal import CBioPortalIntegrator


@respx.mock
async def test_fetch_gene_frequency() -> None:
    respx.get(
        url__regex=r"https://www\.cbioportal\.org/api/molecular-profiles/.*/mutations.*"
    ).mock(
        return_value=Response(
            200,
            json=[
                {"sampleId": "S1", "gene": {"hugoGeneSymbol": "TP53"}, "proteinChange": "R175H"},
                {"sampleId": "S2", "gene": {"hugoGeneSymbol": "TP53"}, "proteinChange": "R248Q"},
            ],
        )
    )
    i = CBioPortalIntegrator(cache=None)
    r = await i.fetch("mutations:lihc_tcga:TP53")
    assert r["total_mutations"] == 2
    assert r["gene"] == "TP53"


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r"https://www\.cbioportal\.org/.*").mock(
        return_value=Response(500)
    )
    i = CBioPortalIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("mutations:lihc_tcga:TP53")


def test_family_is_F5() -> None:
    assert CBioPortalIntegrator(cache=None).family == "F5"
