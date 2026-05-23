"""Test ClinicalTrialsGovIntegrator — CT.gov v2 API."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.clinicaltrials import ClinicalTrialsGovIntegrator


@respx.mock
async def test_fetch_nct_returns_study() -> None:
    respx.get(url__regex=r"https://clinicaltrials\.gov/api/v2/studies/NCT01234567.*").mock(
        return_value=Response(200, json={
            "protocolSection": {
                "identificationModule": {"nctId": "NCT01234567", "briefTitle": "Test trial"},
                "statusModule": {"overallStatus": "RECRUITING"},
                "conditionsModule": {"conditions": ["HCC"]},
                "armsInterventionsModule": {"interventions": [{"name": "DrugX"}]},
                "eligibilityModule": {"eligibilityCriteria": "Adults; ECOG 0-1"},
            }
        })
    )
    i = ClinicalTrialsGovIntegrator(cache=None)
    r = await i.fetch("NCT:NCT01234567")
    assert r["nct_id"] == "NCT01234567"
    assert r["status"] == "RECRUITING"
    assert "HCC" in r["conditions"]


@respx.mock
async def test_fetch_search_returns_studies() -> None:
    respx.get(url__regex=r"https://clinicaltrials\.gov/api/v2/studies\?.*").mock(
        return_value=Response(200, json={
            "studies": [
                {"protocolSection": {
                    "identificationModule": {"nctId": "NCT02", "briefTitle": "S2"},
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "conditionsModule": {"conditions": ["NSCLC EGFR"]},
                    "armsInterventionsModule": {"interventions": [{"name": "Amivantamab"}]},
                    "eligibilityModule": {"eligibilityCriteria": "..."},
                }}
            ]
        })
    )
    i = ClinicalTrialsGovIntegrator(cache=None)
    r = await i.fetch("search:NSCLC EGFR osimertinib resistance")
    assert len(r["studies"]) == 1
    assert r["studies"][0]["nct_id"] == "NCT02"


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r"https://clinicaltrials\.gov/.*").mock(return_value=Response(500))
    i = ClinicalTrialsGovIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("NCT:NCT99")


def test_family_is_F3() -> None:
    assert ClinicalTrialsGovIntegrator(cache=None).family == "F3"
