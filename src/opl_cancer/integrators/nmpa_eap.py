"""NMPA 临床急需进口药品 list scrape. Spec §2.5 F8."""
from __future__ import annotations

import re
from typing import Any

import httpx

from .base import Integrator, IntegratorError


_URL = "https://www.nmpa.gov.cn/yaopin/ypjgdt/index.html"  # 公开列表入口


class NMPAEAPIntegrator(Integrator):
    family = "F8"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"NMPA EAP: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                r = await http.get(_URL)
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"NMPA transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"NMPA HTTP {r.status_code}")

        rows = re.findall(
            r"<tr[^>]*>\s*<td[^>]*>[^<]*</td>\s*"
            r"<td[^>]*>([^<]+)</td>\s*"
            r"<td[^>]*>([^<]+)</td>\s*"
            r"<td[^>]*>([^<]+)</td>",
            r.text,
            re.DOTALL,
        )
        entries = [
            {"drug": drug.strip(), "indication": ind.strip(), "date": date.strip()}
            for drug, ind, date in rows
            if term in (drug + ind)
        ]
        return {"query": term, "entries": entries, "source_url": _URL}
