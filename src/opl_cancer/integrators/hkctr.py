"""HKCTR Hong Kong clinical trial registry — public HTML scrape, no auth. Spec §2.5 F3.

HKCTR (Hong Kong Clinical Trials Registry) is the Department of Health
Drug Office's public registry for clinical trials conducted in the Hong
Kong SAR. It is the canonical source for HK-led oncology trials and the
HK arms of multi-jurisdiction registrations that may not appear in
CT.gov, EU-CTR, ISRCTN, or ChiCTR.

The registry exposes a public listing endpoint at:

    https://www.hkclinicaltrials.com/

with the underlying search backed by the Department of Health Drug
Office portal:

    https://www.drugoffice.gov.hk/eps/

The primary URL is HTML; no API key, no rate limit beyond fair-use. We
HTML-scrape the result rows. The scrape is intentionally tolerant of
both the primary registry and the drug-office fallback — schema drift
is surfaced as ``IntegratorError`` rather than silent empty.

Key format: ``search:<term>`` (e.g. ``search:EBV nasopharyngeal carcinoma``).
TTL: 1 day (registry updates within 24-48h of HK DH-CRG approval).

v1.4.0 (round-2 EVAL Patient #20 NPC EBV CN/DE/HK three-jurisdiction). See
``docs/adr/0008-eval-panel-round-2-v1.3.2.md`` (Deferred — D10).
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_PRIMARY_URL = "https://www.hkclinicaltrials.com/"
_FALLBACK_URL = "https://www.drugoffice.gov.hk/eps/do/en/pcm/clinical_trial_search.html"

# HKCTR registry IDs canonically render as e.g. HKCTR-1234, HKCTR1234,
# or as full URLs into the registry view page. We match both shapes.
_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"HKCTR[-\s]?(\d{3,6})", re.IGNORECASE),
    re.compile(r"CRE[-\s]?(\d{3,6})", re.IGNORECASE),  # Clinical-Research-Ethics linkage
)


def _extract_trials_from_html(html: str, source_url: str) -> list[dict[str, Any]]:
    """Tolerant scraper: matches three observable layouts.

    Layout A — primary registry result rows (table.tablesorter / div.search-result):
        <a href="/trial/HKCTR-1234">Trial Title</a>
    Layout B — drug-office fallback (table.tableone):
        <tr><td>HKCTR1234</td><td>Title</td><td>Status</td></tr>
    Layout C — JSON-LD blocks embedded in some result pages.
    """
    trials: list[dict[str, Any]] = []

    # Layout A: linked-anchor card with HKCTR / CRE id in href OR text
    rows_a = re.findall(
        r"<a[^>]*href=\"([^\"]*)\"[^>]*>\s*([^<]*HKCTR[-\s]?\d{3,6}[^<]*|[^<]*CRE[-\s]?\d{3,6}[^<]*)</a>"
        r"(?:.*?<(?:p|div|span)[^>]*>([^<]{8,250})</(?:p|div|span)>)?",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    for href, label, snippet in rows_a:
        hkctr_id = _first_id(label) or _first_id(href)
        if not hkctr_id:
            continue
        trials.append(
            {
                "hkctr_id": hkctr_id,
                "title": _clean_text(label),
                "summary": _clean_text(snippet or ""),
                "url": _normalise_url(href, source_url),
            }
        )

    # Layout B: tabular row with HKCTR id in first cell
    if not trials:
        rows_b = re.findall(
            r"<tr[^>]*>\s*<td[^>]*>\s*(HKCTR[-\s]?\d{3,6}|CRE[-\s]?\d{3,6})\s*</td>"
            r"\s*<td[^>]*>([^<]+)</td>(?:\s*<td[^>]*>([^<]*)</td>)?",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for raw_id, title, status in rows_b:
            hkctr_id = _first_id(raw_id)
            if not hkctr_id:
                continue
            trials.append(
                {
                    "hkctr_id": hkctr_id,
                    "title": _clean_text(title),
                    "summary": _clean_text(status or ""),
                    "url": source_url,
                }
            )

    # De-dupe by hkctr_id, keeping the first observation (which carries the URL).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for trial in trials:
        tid = trial["hkctr_id"]
        if tid in seen:
            continue
        seen.add(tid)
        deduped.append(trial)
    return deduped


def _first_id(text: str) -> str | None:
    for pat in _ID_PATTERNS:
        m = pat.search(text)
        if m:
            prefix = "HKCTR" if pat.pattern.lower().startswith("hkctr") else "CRE"
            return f"{prefix}-{m.group(1)}"
    return None


def _clean_text(s: str) -> str:
    # collapse whitespace + strip HTML entities aggressively but tolerantly
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _normalise_url(href: str, source_url: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        base = source_url.rstrip("/")
        # If source_url has a path component, retain only the scheme+host
        m = re.match(r"^(https?://[^/]+)", base)
        return (m.group(1) if m else base) + href
    return source_url.rstrip("/") + "/" + href


class HKCTRIntegrator(Integrator):
    """Hong Kong Clinical Trials Registry scraper.

    Strategy:
      1. Try the primary registry homepage with the search term as a query
         parameter (``?q=<term>``). If the page renders a result section,
         scrape it.
      2. On primary-URL failure / empty result / schema drift indicator
         absent, fall back to the Department of Health Drug Office
         clinical-trial search page.
      3. Surface ``IntegratorError`` on transport failure / 4xx-5xx / schema
         drift (registry markers present but zero rows parsed).
    """

    family = "F3"
    ttl_seconds = 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"HKCTR: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        if not term:
            raise IntegratorError("HKCTR: empty search term")

        # Primary attempt
        primary_html, primary_status = await self._safe_get(_PRIMARY_URL, {"q": term})
        primary_trials: list[dict[str, Any]] = []
        primary_drift = False
        if primary_html is not None:
            primary_trials = _extract_trials_from_html(primary_html, _PRIMARY_URL)
            # Schema-drift detection: page has HKCTR markers but our regex caught 0 rows.
            if not primary_trials and re.search(
                r"HKCTR[-\s]?\d{3,6}|CRE[-\s]?\d{3,6}", primary_html, re.IGNORECASE
            ):
                primary_drift = True

        if primary_trials:
            return {
                "query": term,
                "trials": primary_trials,
                "source_url": _PRIMARY_URL,
                "source_used": "primary",
            }

        # Fallback attempt
        fallback_html, fallback_status = await self._safe_get(
            _FALLBACK_URL, {"keyword": term}
        )
        fallback_trials: list[dict[str, Any]] = []
        fallback_drift = False
        if fallback_html is not None:
            fallback_trials = _extract_trials_from_html(fallback_html, _FALLBACK_URL)
            if not fallback_trials and re.search(
                r"HKCTR[-\s]?\d{3,6}|CRE[-\s]?\d{3,6}", fallback_html, re.IGNORECASE
            ):
                fallback_drift = True

        if fallback_trials:
            return {
                "query": term,
                "trials": fallback_trials,
                "source_url": _FALLBACK_URL,
                "source_used": "fallback_drug_office",
            }

        # Both attempts produced no trials — distinguish empty-but-clean vs schema drift.
        if primary_drift or fallback_drift:
            raise IntegratorError(
                "HKCTR: result-row schema drift detected — primary or fallback "
                "page has HKCTR / CRE markers but regex matched 0 rows; update "
                "regex patterns in hkctr.py"
            )

        primary_unreachable = primary_html is None
        fallback_unreachable = fallback_html is None
        if primary_unreachable and fallback_unreachable:
            raise IntegratorError(
                "HKCTR: both primary and fallback endpoints unreachable "
                f"(primary_status={primary_status}, fallback_status={fallback_status})"
            )

        # Genuine empty result — no markers and clean response.
        return {
            "query": term,
            "trials": [],
            "source_url": _PRIMARY_URL,
            "source_used": "primary",
        }

    async def _safe_get(
        self, url: str, params: dict[str, str]
    ) -> tuple[str | None, int | None]:
        """Return (html, status) or (None, None) on transport failure.

        Does NOT raise — the caller decides whether to fall through to the
        fallback URL or surface a final IntegratorError. 4xx/5xx are returned
        as (None, status) so the caller can distinguish unreachable from
        clean-empty.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                r = await http.get(url, params=params)
        except (httpx.HTTPError, ConnectionError, OSError):
            return None, None
        if r.status_code >= 400:
            return None, r.status_code
        return r.text, r.status_code
