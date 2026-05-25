"""EMA compassionate-use / Article-83 navigation — public HTML scrape. Spec §2.5 F8.

The EMA hosts a compassionate-use information surface listing CHMP
opinions, recommended-for-compassionate-use products (Regulation
(EC) 726/2004 Article 83), and member-state implementation pointers.
There is no official REST API for compassionate-use entries; the surface
is a search-driven HTML directory under:

    https://www.ema.europa.eu/en/human-regulatory/research-development/compassionate-use

We HTML-scrape result cards. EMA implementation of compassionate use is
**national** (each Member State runs its own pathway under EMA opinion);
this integrator emits the EMA-level opinion + product page, and downstream
Dennis / Frances are expected to overlay the patient's specific Member
State pathway (national NCA — e.g. AIFA Italy, BfArM Germany, ANSM France).

Key format: ``search:<term>`` (e.g. ``search:olaparib`` or
``search:lutetium`` or ``search:metastatic colorectal``).
TTL: 7 days.
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_BASE_URL = "https://www.ema.europa.eu"
_SEARCH_URL = f"{_BASE_URL}/en/search"


class EMAEAPIntegrator(Integrator):
    family = "F8"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"EMA EAP: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        if not term:
            raise IntegratorError("EMA EAP: empty search term")
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "opl-cancer-skill/1.3 (+CancerDAO)"},
            ) as http:
                r = await http.get(
                    _SEARCH_URL,
                    params={
                        "search_api_fulltext": term,
                        "f[0]": "ema_search_categories:83",  # compassionate-use facet
                    },
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"EMA transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"EMA HTTP {r.status_code}")

        html = r.text
        # Match result cards: link + title + truncated summary.
        rows = re.findall(
            r"<article[^>]*class=\"[^\"]*node[^\"]*\"[^>]*>.*?"
            r"<a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>"
            r"(?:.*?<div[^>]*class=\"[^\"]*field[^\"]*body[^\"]*\"[^>]*>([^<]+)</div>)?",
            html,
            re.DOTALL,
        )
        entries = [
            {
                "title": title.strip(),
                "url": href if href.startswith("http") else _BASE_URL + href,
                "summary": (summary or "").strip(),
                "compassionate_use_facet": "Article-83",
            }
            for href, title, summary in rows
        ]
        return {
            "query": term,
            "entries": entries,
            "source_url": _SEARCH_URL,
            "member_state_overlay_note": (
                "EMA opinion is EU-level; compassionate-use implementation is "
                "Member-State national (AIFA / BfArM / ANSM / AEMPS / etc). "
                "Dennis / Frances apply the patient-jurisdiction overlay."
            ),
        }
