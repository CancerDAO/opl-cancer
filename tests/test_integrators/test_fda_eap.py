"""Test FDAEAPIntegrator — openFDA expanded access search."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.fda_eap import FDAEAPIntegrator


@respx.mock
async def test_fetch_expanded_access() -> None:
    respx.get(url__regex=r"https://api\.fda\.gov/drug/drugsfda\.json.*").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "application_number": "ANDA000001",
                        "openfda": {
                            "brand_name": ["DrugX"],
                            "generic_name": ["genericx"],
                        },
                    },
                ]
            },
        )
    )
    i = FDAEAPIntegrator(cache=None)
    r = await i.fetch("search:NSCLC EGFR amivantamab")
    assert r["entries"]


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r"https://api\.fda\.gov/.*").mock(return_value=Response(500))
    i = FDAEAPIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("search:x")


def test_family_is_F8() -> None:
    assert FDAEAPIntegrator(cache=None).family == "F8"
