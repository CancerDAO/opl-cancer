"""FDA Expanded Access via openFDA drug/drugsfda endpoint. Spec §2.5 F8."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


class FDAEAPIntegrator(Integrator):
    family = "F8"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("search:"):
            raise IntegratorError(f"FDA EAP: expected search:<term>, got {key!r}")
        term = key[7:].strip()
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    "https://api.fda.gov/drug/drugsfda.json",
                    params={"search": term, "limit": 10},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"FDA transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"FDA HTTP {r.status_code}: {r.text}")
        body = r.json()
        results = body.get("results", [])
        entries = [
            {
                "application_number": e.get("application_number", ""),
                "brand_names": (e.get("openfda") or {}).get("brand_name", []),
                "generic_names": (e.get("openfda") or {}).get("generic_name", []),
            }
            for e in results
        ]
        return {"query": term, "entries": entries}
