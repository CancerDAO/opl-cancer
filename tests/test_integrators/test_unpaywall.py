"""Test UnpaywallIntegrator — DOI → OA full-text URL."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.unpaywall import UnpaywallIntegrator


@respx.mock
async def test_fetch_returns_oa_url() -> None:
    respx.get(url__regex=r"https://api\.unpaywall\.org/v2/10\.1234.*").mock(
        return_value=Response(200, json={
            "doi": "10.1234/abc",
            "is_oa": True,
            "best_oa_location": {"url_for_pdf": "https://oa.example/pdf"},
        })
    )
    i = UnpaywallIntegrator(cache=None, contact_email="test@example.com")
    r = await i.fetch("DOI:10.1234/abc")
    assert r["is_oa"] is True
    assert r["pdf_url"] == "https://oa.example/pdf"


@respx.mock
async def test_fetch_raises_on_404() -> None:
    respx.get(url__regex=r"https://api\.unpaywall\.org/.*").mock(return_value=Response(404))
    i = UnpaywallIntegrator(cache=None, contact_email="test@example.com")
    with pytest.raises(IntegratorError):
        await i.fetch("DOI:10.0/missing")


def test_family_is_F1() -> None:
    assert UnpaywallIntegrator(cache=None, contact_email="x@x").family == "F1"
