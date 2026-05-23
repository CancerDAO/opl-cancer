"""GDC / TCGA cohort lookup. Spec §2.5 F5."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .base import Integrator, IntegratorError


class GDCIntegrator(Integrator):
    family = "F5"
    ttl_seconds = 30 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("project:"):
            raise IntegratorError(f"GDC: expected project:<project_id>, got {key!r}")
        project_id = key[8:].strip()
        filters = {
            "op": "in",
            "content": {"field": "project.project_id", "value": [project_id]},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    "https://api.gdc.cancer.gov/cases",
                    params={"filters": json.dumps(filters), "size": 5},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"GDC transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"GDC HTTP {r.status_code}: {r.text}")
        body = r.json().get("data", {})
        return {
            "project": project_id,
            "total_cases": int(body.get("pagination", {}).get("total", 0)),
            "sample_hits": body.get("hits", []),
        }
