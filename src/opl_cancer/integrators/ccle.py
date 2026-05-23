"""CCLE cell-line expression integrator. Spec §2.5 F7, P3-T5.

Key format: ``<GENE>:<DEPMAP_ID>`` (e.g. ``EGFR:ACH-000001``).
Returns TPM expression value via DepMap portal.
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError

_BASE = "https://depmap.org/portal/api"


class CCLEIntegrator(Integrator):
    family = "F7"
    ttl_seconds = 30 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if ":" not in key:
            raise IntegratorError(
                f"CCLE: key must be '<GENE>:<DEPMAP_ID>', got {key!r}"
            )
        gene, depmap_id = (s.strip() for s in key.split(":", 1))
        if not gene or not depmap_id:
            raise IntegratorError(f"CCLE: empty gene or depmap_id in {key!r}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    f"{_BASE}/expression",
                    params={"gene": gene, "depmap_id": depmap_id},
                    headers={"Accept": "application/json"},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"CCLE transport: {e}") from e
        if r.status_code == 404:
            raise IntegratorError(f"CCLE: {gene} x {depmap_id} not found")
        if r.status_code >= 400:
            raise IntegratorError(f"CCLE HTTP {r.status_code}: {r.text}")
        data = r.json()
        return {
            "gene": gene,
            "depmap_id": depmap_id,
            "tpm": data.get("tpm"),
            "cell_line_name": data.get("cell_line_name", ""),
            "lineage": data.get("lineage", ""),
            "raw": data,
        }
