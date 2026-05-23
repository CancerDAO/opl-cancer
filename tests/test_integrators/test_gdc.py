"""Test GDCIntegrator — TCGA / GDC cohort lookup."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.gdc import GDCIntegrator


@respx.mock
async def test_fetch_project_case_count() -> None:
    respx.get(url__regex=r"https://api\.gdc\.cancer\.gov/cases\?.*").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "pagination": {"total": 377},
                    "hits": [{"case_id": "abc", "submitter_id": "TCGA-XX-1"}],
                }
            },
        )
    )
    i = GDCIntegrator(cache=None)
    r = await i.fetch("project:TCGA-LIHC")
    assert r["total_cases"] == 377


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r"https://api\.gdc\.cancer\.gov/.*").mock(
        return_value=Response(500)
    )
    i = GDCIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("project:TCGA-LIHC")


def test_family_is_F5() -> None:
    assert GDCIntegrator(cache=None).family == "F5"
