"""Test HKCTRIntegrator — Hong Kong Clinical Trials Registry scrape.

Covers:
  * Primary endpoint linked-anchor layout extraction.
  * Drug-office fallback tabular layout extraction.
  * Schema-drift detection (markers present, zero rows parsed → raise).
  * Both endpoints unreachable → raise.
  * Genuine empty (no markers, clean response) → return empty list, no raise.
  * family == "F3".
"""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.hkctr import HKCTRIntegrator


_PRIMARY_HTML_LAYOUT_A = """<html><body>
<div class="search-result">
  <a href="/trial/HKCTR-1234">HKCTR-1234 EBV-specific cytotoxic T-lymphocyte trial for NPC</a>
  <p>Phase II open-label single-arm; recruiting at Prince of Wales Hospital.</p>
</div>
<div class="search-result">
  <a href="/trial/HKCTR-5678">HKCTR-5678 — Adjuvant tislelizumab in NPC EBV-driven post-CRT</a>
  <p>Recruiting; Queen Mary Hospital + Prince of Wales Hospital sites.</p>
</div>
</body></html>"""


_FALLBACK_HTML_LAYOUT_B = """<html><body>
<table class="tableone">
  <tbody>
    <tr><td>HKCTR1234</td><td>EBV-CTL infusion for NPC R/R</td><td>Recruiting</td></tr>
    <tr><td>CRE-9012</td><td>Camrelizumab adjuvant NPC</td><td>Active not recruiting</td></tr>
  </tbody>
</table>
</body></html>"""


_EMPTY_CLEAN_HTML = """<html><body>
<div class="search-result-empty">No matching trials.</div>
</body></html>"""


_DRIFT_HTML = """<html><body>
<div>HKCTR-1234 EBV trial — but markup changed; our regex misses this layout.</div>
<span>Status: HKCTR9999 active</span>
</body></html>"""


@respx.mock
async def test_primary_returns_trials() -> None:
    respx.get(url__regex=r"https?://www\.hkclinicaltrials\.com/.*").mock(
        return_value=Response(200, text=_PRIMARY_HTML_LAYOUT_A)
    )
    i = HKCTRIntegrator(cache=None)
    r = await i.fetch("search:EBV nasopharyngeal carcinoma")
    assert r["source_used"] == "primary"
    assert len(r["trials"]) == 2
    ids = {t["hkctr_id"] for t in r["trials"]}
    assert "HKCTR-1234" in ids
    assert "HKCTR-5678" in ids


@respx.mock
async def test_fallback_drug_office_when_primary_empty() -> None:
    # Primary returns clean-empty
    respx.get(url__regex=r"https?://www\.hkclinicaltrials\.com/.*").mock(
        return_value=Response(200, text=_EMPTY_CLEAN_HTML)
    )
    respx.get(url__regex=r"https?://www\.drugoffice\.gov\.hk/.*").mock(
        return_value=Response(200, text=_FALLBACK_HTML_LAYOUT_B)
    )
    i = HKCTRIntegrator(cache=None)
    r = await i.fetch("search:NPC EBV")
    assert r["source_used"] == "fallback_drug_office"
    assert len(r["trials"]) == 2
    ids = {t["hkctr_id"] for t in r["trials"]}
    assert "HKCTR-1234" in ids
    assert "CRE-9012" in ids


@respx.mock
async def test_schema_drift_raises() -> None:
    # Primary has markers but zero rows match; fallback also drifts.
    respx.get(url__regex=r"https?://www\.hkclinicaltrials\.com/.*").mock(
        return_value=Response(200, text=_DRIFT_HTML)
    )
    respx.get(url__regex=r"https?://www\.drugoffice\.gov\.hk/.*").mock(
        return_value=Response(200, text=_DRIFT_HTML)
    )
    i = HKCTRIntegrator(cache=None)
    with pytest.raises(IntegratorError, match="schema drift"):
        await i.fetch("search:anything")


@respx.mock
async def test_both_endpoints_unreachable_raises() -> None:
    respx.get(url__regex=r"https?://www\.hkclinicaltrials\.com/.*").mock(
        return_value=Response(503)
    )
    respx.get(url__regex=r"https?://www\.drugoffice\.gov\.hk/.*").mock(
        return_value=Response(500)
    )
    i = HKCTRIntegrator(cache=None)
    with pytest.raises(IntegratorError, match="unreachable"):
        await i.fetch("search:anything")


@respx.mock
async def test_genuine_empty_no_raise() -> None:
    # Both endpoints return clean-empty (no HKCTR markers) — should return empty list, not raise.
    respx.get(url__regex=r"https?://www\.hkclinicaltrials\.com/.*").mock(
        return_value=Response(200, text=_EMPTY_CLEAN_HTML)
    )
    respx.get(url__regex=r"https?://www\.drugoffice\.gov\.hk/.*").mock(
        return_value=Response(200, text=_EMPTY_CLEAN_HTML)
    )
    i = HKCTRIntegrator(cache=None)
    r = await i.fetch("search:totally unrelated query xyz123")
    assert r["trials"] == []


async def test_rejects_non_search_key() -> None:
    i = HKCTRIntegrator(cache=None)
    with pytest.raises(IntegratorError, match="expected search:"):
        await i.fetch("pmid:12345")


async def test_rejects_empty_term() -> None:
    i = HKCTRIntegrator(cache=None)
    with pytest.raises(IntegratorError, match="empty search term"):
        await i.fetch("search:")


def test_family_is_F3() -> None:
    assert HKCTRIntegrator(cache=None).family == "F3"
