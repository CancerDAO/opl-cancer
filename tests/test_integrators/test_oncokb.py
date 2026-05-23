"""Test OncoKBIntegrator — variant actionability."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.oncokb import OncoKBIntegrator


@respx.mock
async def test_fetch_actionable_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONCOKB_API_KEY", "test-token")
    respx.get(
        url__regex=r"https://www\.oncokb\.org/api/v1/annotate/mutations/byProteinChange.*"
    ).mock(
        return_value=Response(200, json={
            "geneExist": True,
            "variantExist": True,
            "oncogenic": "Oncogenic",
            "highestSensitiveLevel": "LEVEL_1",
            "treatments": [{"drugs": [{"drugName": "Osimertinib"}], "level": "LEVEL_1"}],
        })
    )
    i = OncoKBIntegrator(cache=None)
    r = await i.fetch("EGFR:L858R:NSCLC")
    assert r["oncogenic"] == "Oncogenic"
    assert r["highest_level"] == "LEVEL_1"
    assert any(t["drug"] == "Osimertinib" for t in r["treatments"])


@respx.mock
async def test_fetch_raises_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONCOKB_API_KEY", "bad")
    respx.get(url__regex=r"https://www\.oncokb\.org/.*").mock(return_value=Response(401))
    i = OncoKBIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("EGFR:L858R:NSCLC")


def test_oncokb_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ONCOKB_API_KEY", raising=False)
    with pytest.raises(IntegratorError):
        OncoKBIntegrator(cache=None)


def test_family_is_F4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONCOKB_API_KEY", "x")
    assert OncoKBIntegrator(cache=None).family == "F4"
