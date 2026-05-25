"""P0-2: NCBI eutils requires tool= and email= on every call.

Without these, NCBI rate-limits anonymous traffic and may IP-ban bursts
(https://www.ncbi.nlm.nih.gov/books/NBK25497/). All 4 of our NCBI integrators
(PubMed, ClinVar, GEO, SRA) must inject identity params.
"""
from __future__ import annotations

import os

import pytest
import respx
from httpx import Response

from opl_cancer.integrators._ncbi import ncbi_identity_params, with_ncbi_identity


def test_identity_has_required_fields() -> None:
    params = ncbi_identity_params()
    assert params["tool"] == "opl-cancer"
    assert "@" in params["email"]
    # api_key is optional, only present when env set
    if "NCBI_API_KEY" not in os.environ:
        assert "api_key" not in params


def test_with_ncbi_identity_merges_without_overwriting_caller_params() -> None:
    merged = with_ncbi_identity({"db": "pubmed", "tool": "override"})
    assert merged["db"] == "pubmed"
    assert merged["tool"] == "override"  # caller wins
    assert "email" in merged


def test_env_override_applies(monkeypatch) -> None:
    monkeypatch.setenv("OPL_NCBI_EMAIL", "test@example.com")
    monkeypatch.setenv("OPL_NCBI_TOOL", "my-fork")
    monkeypatch.setenv("NCBI_API_KEY", "abc123")
    p = ncbi_identity_params()
    assert p == {"tool": "my-fork", "email": "test@example.com", "api_key": "abc123"}


@pytest.mark.asyncio
@respx.mock
async def test_pubmed_sends_tool_and_email_on_efetch() -> None:
    """End-to-end: a real PubMedIntegrator.fetch() must include tool+email in request URL."""
    from opl_cancer.integrators.pubmed import PubMedIntegrator

    captured: dict[str, str] = {}

    def _capture(request):
        for k, v in request.url.params.items():
            captured[k] = v
        return Response(
            200,
            text=(
                "<PubmedArticleSet><PubmedArticle><MedlineCitation><Article>"
                "<ArticleTitle>T</ArticleTitle>"
                "<Abstract><AbstractText>A</AbstractText></Abstract>"
                "<Journal><Title>J</Title></Journal>"
                "</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
            ),
        )

    respx.get(url__regex=r"https://eutils\.ncbi\.nlm\.nih\.gov/.*efetch\.fcgi.*").mock(
        side_effect=_capture
    )

    integ = PubMedIntegrator(cache=None)
    out = await integ.fetch("PMID:12345")
    assert out["pmid"] == "12345"
    assert captured.get("tool") == "opl-cancer"
    assert "@" in captured.get("email", "")


@pytest.mark.asyncio
@respx.mock
async def test_clinvar_sends_tool_and_email() -> None:
    from opl_cancer.integrators.clinvar import ClinVarIntegrator

    captured_per_call: list[dict[str, str]] = []

    def _capture(request):
        captured_per_call.append({k: v for k, v in request.url.params.items()})
        path = request.url.path
        if "esearch" in path:
            return Response(200, json={"esearchresult": {"idlist": ["999"]}})
        return Response(
            200,
            json={"result": {"999": {"title": "T", "clinical_significance": {"description": "Benign"}, "trait_set": []}}},
        )

    respx.get(url__regex=r"https://eutils\.ncbi\.nlm\.nih\.gov/.*").mock(side_effect=_capture)
    integ = ClinVarIntegrator(cache=None)
    await integ.fetch("variant:BRCA1 c.5266dupC")
    assert len(captured_per_call) >= 2
    for call_params in captured_per_call:
        assert call_params.get("tool") == "opl-cancer"
        assert "@" in call_params.get("email", "")
