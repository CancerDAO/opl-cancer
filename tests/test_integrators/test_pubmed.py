"""Test PubMedIntegrator — esearch + efetch via NCBI E-utilities."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.pubmed import PubMedIntegrator


_EFETCH_XML = """<?xml version='1.0'?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>38219045</PMID>
      <Article>
        <ArticleTitle>WNT signaling in HCC</ArticleTitle>
        <Abstract><AbstractText>WNT/β-catenin activation correlated with reduced ICI response (HR 2.10, 95%CI 1.32-3.36)</AbstractText></Abstract>
        <Journal><Title>Nature</Title></Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

_ESEARCH_JSON = {
    "esearchresult": {"idlist": ["38219045"], "count": "1"}
}


@respx.mock
async def test_fetch_pmid_returns_record(tmp_path) -> None:
    respx.get(url__regex=r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi.*").mock(
        return_value=Response(200, text=_EFETCH_XML)
    )
    integ = PubMedIntegrator(cache=None)
    rec = await integ.fetch("PMID:38219045")
    assert rec["pmid"] == "38219045"
    assert "WNT signaling" in rec["title"]
    assert "HR 2.10" in rec["abstract"]


@respx.mock
async def test_fetch_search_returns_top_records() -> None:
    respx.get(url__regex=r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi.*").mock(
        return_value=Response(200, json=_ESEARCH_JSON)
    )
    respx.get(url__regex=r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi.*").mock(
        return_value=Response(200, text=_EFETCH_XML)
    )
    integ = PubMedIntegrator(cache=None)
    rec = await integ.fetch("search:WNT HCC ICI")
    assert rec["pmid"] == "38219045"


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r".*efetch.*").mock(return_value=Response(500))
    integ = PubMedIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("PMID:99999999")


@respx.mock
async def test_fetch_raises_on_empty_search() -> None:
    respx.get(url__regex=r".*esearch.*").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": [], "count": "0"}})
    )
    integ = PubMedIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("search:nonsense gibberish xyzzy")


def test_pubmed_family_is_F1() -> None:
    integ = PubMedIntegrator(cache=None)
    assert integ.family == "F1"
