"""Unpaywall — OA full-text URL by DOI. Spec §2.5 F1."""
from __future__ import annotations

import os
from typing import Any

import httpx

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


class UnpaywallIntegrator(Integrator):
    family = "F1"
    ttl_seconds = 30 * 24 * 3600  # OA status changes slowly

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        contact_email: str | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self.email = contact_email or os.environ.get("UNPAYWALL_EMAIL", "")
        if not self.email:
            raise IntegratorError("UNPAYWALL_EMAIL required by Unpaywall ToS")

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("DOI:"):
            raise IntegratorError(f"Unpaywall: expected DOI:<doi>, got {key!r}")
        doi = key[4:].strip()
        try:
            async with httpx.AsyncClient(timeout=20.0) as http:
                r = await http.get(
                    f"https://api.unpaywall.org/v2/{doi}",
                    params={"email": self.email},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"Unpaywall transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"Unpaywall HTTP {r.status_code}: {r.text}")
        body = r.json()
        best = body.get("best_oa_location") or {}
        return {
            "doi": body.get("doi", doi),
            "is_oa": bool(body.get("is_oa")),
            "pdf_url": best.get("url_for_pdf"),
            "html_url": best.get("url"),
            "license": best.get("license"),
        }
