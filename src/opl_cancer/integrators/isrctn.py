"""ISRCTN UK trial registry — public HTML scrape, no auth. Spec §2.5 F3.

ISRCTN is the UK / Ireland public clinical trial registry (formerly
Current Controlled Trials). It is the canonical source for UK / NHS-led
oncology trials that may not appear in CT.gov (e.g. CRUK-sponsored
academic studies, NIHR portfolio cancer trials).

The registry exposes a public search endpoint at
``https://www.isrctn.com/search`` returning HTML; no API key, no rate
limit beyond fair-use. We HTML-scrape the result rows. The scrape is
intentionally tolerant (matches the visible card pattern) — schema drift
is surfaced as ``IntegratorError`` rather than silent empty.

Key format: ``search:<term>`` (e.g. ``search:olaparib BRCA2 prostate``).
TTL: 1 day (registry updates within 24-48h of CRG approval).
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_SEARCH_URL = "https://www.isrctn.com/search"


class ISRCTNIntegrator(Integrator):
    family = "F3"
    ttl_seconds = 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"ISRCTN: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        if not term:
            raise IntegratorError("ISRCTN: empty search term")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                r = await http.get(_SEARCH_URL, params={"q": term})
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"ISRCTN transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"ISRCTN HTTP {r.status_code}")

        html = r.text
        # Match the result-card layout: ISRCTN number + linked title + short
        # snippet. Pattern intentionally tolerant — surfaces a clear schema-
        # drift error if zero rows parse from a non-empty page.
        rows = re.findall(
            r"<a[^>]*href=\"(/ISRCTN\d{6,10})\"[^>]*>([^<]+)</a>"
            r"(?:.*?<p[^>]*class=\"[^\"]*ResultListItem_summary[^\"]*\"[^>]*>([^<]+)</p>)?",
            html,
            re.DOTALL,
        )
        trials = [
            {
                "isrctn_id": link.lstrip("/"),
                "title": title.strip(),
                "summary": (summary or "").strip(),
                "url": f"https://www.isrctn.com{link}",
            }
            for link, title, summary in rows
        ]
        if not trials and "ResultListItem" in html:
            # Schema drift — page rendered cards but our regex did not match.
            raise IntegratorError(
                "ISRCTN: result-card schema drift detected — page has "
                "ResultListItem markers but regex matched 0 rows; update "
                "regex in isrctn.py"
            )
        return {"query": term, "trials": trials, "source_url": _SEARCH_URL}
