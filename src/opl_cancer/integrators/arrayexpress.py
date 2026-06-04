"""EBI ArrayExpress / BioStudies integrator. Spec §2.5 F6, P3-T2.

Accession formats: E-MTAB-XXXX / E-GEOD-XXXX / E-PROT-XXXX.
Uses BioStudies REST API. no-silent-fallback policy — raise on failure.
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError

_BASE = "https://www.ebi.ac.uk/biostudies/api/v1"


class ArrayExpressIntegrator(Integrator):
    family = "F6"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        accession = key.strip().upper()
        if not accession.startswith("E-"):
            raise IntegratorError(
                f"ArrayExpress: unrecognised key {key!r}; expected E-XXX-NNNN accession"
            )
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    f"{_BASE}/studies/{accession}",
                    headers={"Accept": "application/json"},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"ArrayExpress transport: {e}") from e
        if r.status_code == 404:
            raise IntegratorError(f"ArrayExpress: accession {accession} not found")
        if r.status_code >= 400:
            raise IntegratorError(
                f"ArrayExpress HTTP {r.status_code}: {r.text}"
            )
        data = r.json()
        sec = data.get("section", {})
        attrs = {a.get("name"): a.get("value") for a in sec.get("attributes", [])}
        return {
            "accession": data.get("accno") or accession,
            "title": attrs.get("Title", ""),
            "description": attrs.get("Description", ""),
            "type": sec.get("type", ""),
            "organism": attrs.get("Organism", ""),
            "n_assays": attrs.get("Assays", 0),
            "raw": data,
        }
