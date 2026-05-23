"""ChiCTR (Chinese Clinical Trial Registry) — public HTML scrape.

No official REST API; scrape https://www.chictr.org.cn/searchproj.html.
Failure modes (timeout / HTML schema change / empty result) all raise.
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_SEARCH_URL = "https://www.chictr.org.cn/searchproj.html"


class ChiCTRIntegrator(Integrator):
    family = "F3"
    ttl_seconds = 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"ChiCTR: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                r = await http.get(_SEARCH_URL, params={"title": term})
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"ChiCTR transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"ChiCTR HTTP {r.status_code}")
        html = r.text
        rows = re.findall(
            r"<a[^>]*>(ChiCTR\d{8,12})</a>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([^<]+)</td>",
            html,
            re.DOTALL,
        )
        studies = [
            {"chictr_id": rid, "title": title.strip(), "status": status.strip()}
            for rid, title, status in rows
        ]
        return {"query": term, "studies": studies}
