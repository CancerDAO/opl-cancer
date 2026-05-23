"""DepMapIntegrator tests — F7 P3-T4."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.depmap import DepMapIntegrator


@respx.mock
async def test_fetch_gene_effect() -> None:
    respx.get(url__regex=r".*depmap.org/portal/api/gene_effect.*").mock(
        return_value=Response(
            200,
            json={
                "gene_effect": -0.85,
                "dependency_probability": 0.92,
                "cell_line_name": "HEPG2",
                "lineage": "liver",
            },
        )
    )
    integ = DepMapIntegrator(cache=None)
    rec = await integ.fetch("CTNNB1:ACH-000739")
    assert rec["gene"] == "CTNNB1"
    assert rec["depmap_id"] == "ACH-000739"
    assert rec["gene_effect"] == -0.85
    assert rec["dependency_probability"] == 0.92


async def test_fetch_bad_key_raises() -> None:
    integ = DepMapIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("CTNNB1_no_colon")


@respx.mock
async def test_fetch_404_raises() -> None:
    respx.get(url__regex=r".*depmap.org/portal/api/gene_effect.*").mock(
        return_value=Response(404)
    )
    integ = DepMapIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("FOOBAR:ACH-999999")


def test_depmap_family_is_f7() -> None:
    integ = DepMapIntegrator(cache=None)
    assert integ.family == "F7"
