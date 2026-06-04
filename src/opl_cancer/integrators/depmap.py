"""Broad DepMap cell-line dependency integrator. Spec §2.5 F7, P3-T4.

Key format: ``<GENE>:<CELL_LINE_DEPMAP_ID>`` (e.g. ``TP53:ACH-000001``).
Returns CRISPR gene effect + dependency probability.

NB: DepMap portal API endpoints can change with quarterly releases — on schema
drift we raise IntegratorError (no-silent-fallback policy).
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError

_BASE = "https://depmap.org/portal/api"


class DepMapIntegrator(Integrator):
    family = "F7"
    ttl_seconds = 30 * 24 * 3600  # DepMap releases quarterly

    async def fetch(self, key: str) -> dict[str, Any]:
        if ":" not in key:
            raise IntegratorError(
                f"DepMap: key must be '<GENE>:<DEPMAP_ID>', got {key!r}"
            )
        gene, depmap_id = (s.strip() for s in key.split(":", 1))
        if not gene or not depmap_id:
            raise IntegratorError(f"DepMap: empty gene or depmap_id in {key!r}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    f"{_BASE}/gene_effect",
                    params={"gene": gene, "depmap_id": depmap_id},
                    headers={"Accept": "application/json"},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"DepMap transport: {e}") from e
        if r.status_code == 404:
            raise IntegratorError(f"DepMap: {gene} x {depmap_id} not found")
        if r.status_code >= 400:
            raise IntegratorError(f"DepMap HTTP {r.status_code}: {r.text}")
        data = r.json()
        return {
            "gene": gene,
            "depmap_id": depmap_id,
            "gene_effect": data.get("gene_effect"),
            "dependency_probability": data.get("dependency_probability"),
            "cell_line_name": data.get("cell_line_name", ""),
            "lineage": data.get("lineage", ""),
            "raw": data,
        }
