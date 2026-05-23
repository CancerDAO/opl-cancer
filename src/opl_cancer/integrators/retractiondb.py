"""Retraction lookup via CrossRef relation field. Spec §2.5 F1 + §7 G9."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


class RetractionDBIntegrator(Integrator):
    family = "F1"
    ttl_seconds = 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("DOI:"):
            raise IntegratorError(f"RetractionDB: expected DOI:<doi>, got {key!r}")
        doi = key[4:].strip()
        try:
            async with httpx.AsyncClient(timeout=20.0) as http:
                r = await http.get(f"https://api.crossref.org/works/{doi}")
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"RetractionDB transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"RetractionDB HTTP {r.status_code}: {r.text}")
        msg = r.json().get("message", {})
        retr = (msg.get("relation") or {}).get("is-retracted-by", [])
        if retr:
            return {"doi": doi, "retracted": True, "retraction_doi": retr[0].get("id", "")}
        return {"doi": doi, "retracted": False, "retraction_doi": None}
