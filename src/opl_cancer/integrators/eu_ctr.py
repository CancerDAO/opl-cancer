"""EU Clinical Trials Register (EU-CTR) — public HTML scrape, no auth. Spec §2.5 F3.

EU-CTR (EudraCT) is the EMA / EU public registry for clinical trials
conducted in EU / EEA Member States + UK (legacy). It is the canonical
source for EU-sponsored oncology trials that may not appear in CT.gov.
EU-CTR is being progressively migrated into CTIS (Clinical Trials
Information System) post-2022; both still hold useful data and the
public-facing search lives at:

    https://www.clinicaltrialsregister.eu/ctr-search/

There is no official REST API. We HTML-scrape the result rows.

Key format: ``search:<term>`` (e.g. ``search:enzalutamide PSMA prostate``).
TTL: 1 day (post-CTIS migration the registry updates within 24-72h of EMA
approval).
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_SEARCH_URL = "https://www.clinicaltrialsregister.eu/ctr-search/search"


class EUCTRIntegrator(Integrator):
    family = "F3"
    ttl_seconds = 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"EU-CTR: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        if not term:
            raise IntegratorError("EU-CTR: empty search term")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                r = await http.get(_SEARCH_URL, params={"query": term})
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"EU-CTR transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"EU-CTR HTTP {r.status_code}")

        html = r.text
        # EU-CTR result rows present as a <table class="result"> with one
        # EudraCT number per row plus title.
        rows = re.findall(
            r"<td[^>]*class=\"[^\"]*result[^\"]*\"[^>]*>\s*"
            r"<a[^>]*href=\"([^\"]+)\"[^>]*>(\d{4}-\d{6}-\d{2})</a>"
            r"</td>.*?<td[^>]*>([^<]+)</td>",
            html,
            re.DOTALL,
        )
        trials = [
            {
                "eudract_number": eudract,
                "title": title.strip(),
                "url": (
                    href
                    if href.startswith("http")
                    else f"https://www.clinicaltrialsregister.eu{href}"
                ),
            }
            for href, eudract, title in rows
        ]
        if not trials and "EudraCT" in html and "no results" not in html.lower():
            # Schema drift — page has EudraCT markers but regex matched 0 rows.
            raise IntegratorError(
                "EU-CTR: result-row schema drift detected — page has EudraCT "
                "markers but regex matched 0 rows; update regex in eu_ctr.py"
            )
        return {"query": term, "trials": trials, "source_url": _SEARCH_URL}
