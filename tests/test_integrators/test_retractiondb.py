"""Test RetractionDBIntegrator — CrossRef-based retraction lookup."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.retractiondb import RetractionDBIntegrator


@respx.mock
async def test_fetch_not_retracted() -> None:
    respx.get(url__regex=r"https://api\.crossref\.org/works/10\.1234.*").mock(
        return_value=Response(200, json={"message": {"DOI": "10.1234/ok"}})
    )
    i = RetractionDBIntegrator(cache=None)
    r = await i.fetch("DOI:10.1234/ok")
    assert r["retracted"] is False


@respx.mock
async def test_fetch_retracted_via_relation() -> None:
    respx.get(url__regex=r"https://api\.crossref\.org/works/10\.5555.*").mock(
        return_value=Response(200, json={"message": {
            "DOI": "10.5555/bad",
            "relation": {"is-retracted-by": [{"id": "10.5555/notice"}]},
        }})
    )
    i = RetractionDBIntegrator(cache=None)
    r = await i.fetch("DOI:10.5555/bad")
    assert r["retracted"] is True
    assert r["retraction_doi"] == "10.5555/notice"


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r".*crossref.*").mock(return_value=Response(500))
    i = RetractionDBIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("DOI:10.1/x")


def test_family_is_F1() -> None:
    assert RetractionDBIntegrator(cache=None).family == "F1"
