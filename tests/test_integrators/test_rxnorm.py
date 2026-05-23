"""Test RxNormIntegrator — drug name canonicalization (G3 backbone)."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.rxnorm import RxNormIntegrator


@respx.mock
async def test_fetch_brand_to_generic() -> None:
    respx.get(url__regex=r"https://rxnav\.nlm\.nih\.gov/REST/rxcui\.json.*").mock(
        return_value=Response(200, json={"idGroup": {"rxnormId": ["161"]}})
    )
    respx.get(
        url__regex=r"https://rxnav\.nlm\.nih\.gov/REST/rxcui/161/property\.json.*"
    ).mock(
        return_value=Response(
            200,
            json={
                "propConceptGroup": {
                    "propConcept": [
                        {"propName": "RxNorm Name", "propValue": "acetaminophen"},
                    ]
                }
            },
        )
    )
    i = RxNormIntegrator(cache=None)
    r = await i.fetch("brand:Tylenol")
    assert r["generic"].lower() == "acetaminophen"


@respx.mock
async def test_fetch_raises_on_unknown_drug() -> None:
    respx.get(url__regex=r"https://rxnav\.nlm\.nih\.gov/REST/rxcui\.json.*").mock(
        return_value=Response(200, json={"idGroup": {"rxnormId": []}})
    )
    i = RxNormIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("brand:nonsensicalbrandxyz")


def test_family_is_F10() -> None:
    assert RxNormIntegrator(cache=None).family == "F10"
