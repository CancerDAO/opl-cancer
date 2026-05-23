"""GEOIntegrator tests — F6 P3-T1."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.geo import GEOIntegrator


_ESEARCH_HITS = {"esearchresult": {"idlist": ["200012345"], "count": "1"}}
_ESEARCH_EMPTY = {"esearchresult": {"idlist": [], "count": "0"}}
_ESUMMARY = {
    "result": {
        "200012345": {
            "accession": "GSE12345",
            "title": "scRNA-seq of HCC tumor microenvironment",
            "summary": "Single-cell profile of 12 HCC patients.",
            "n_samples": 24,
            "gpl": "GPL16791",
            "taxon": "Homo sapiens",
        }
    }
}


@respx.mock
async def test_fetch_by_gse_accession() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(
        return_value=Response(200, json=_ESEARCH_HITS)
    )
    respx.get(url__regex=r".*esummary.fcgi.*").mock(
        return_value=Response(200, json=_ESUMMARY)
    )
    integ = GEOIntegrator(cache=None)
    rec = await integ.fetch("GSE12345")
    assert rec["accession"] == "GSE12345"
    assert "scRNA-seq" in rec["title"]
    assert rec["n_samples"] == 24


@respx.mock
async def test_fetch_search_returns_top() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(
        return_value=Response(200, json=_ESEARCH_HITS)
    )
    respx.get(url__regex=r".*esummary.fcgi.*").mock(
        return_value=Response(200, json=_ESUMMARY)
    )
    integ = GEOIntegrator(cache=None)
    rec = await integ.fetch("search:HCC single cell")
    assert rec["accession"] == "GSE12345"


@respx.mock
async def test_fetch_unknown_prefix_raises() -> None:
    integ = GEOIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("PMID:123")


@respx.mock
async def test_fetch_accession_not_found_raises() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(
        return_value=Response(200, json=_ESEARCH_EMPTY)
    )
    integ = GEOIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("GSE99999999")


@respx.mock
async def test_fetch_transport_failure_raises() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(return_value=Response(500))
    integ = GEOIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("GSE12345")


def test_geo_family_is_f6() -> None:
    integ = GEOIntegrator(cache=None)
    assert integ.family == "F6"
