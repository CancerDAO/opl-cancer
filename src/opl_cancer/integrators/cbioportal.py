"""cBioPortal — cancer genomics cohort lookup. Spec §2.5 F5."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


class CBioPortalIntegrator(Integrator):
    family = "F5"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("mutations:"):
            raise IntegratorError(
                f"cBioPortal: expected mutations:<study>:<gene>, got {key!r}"
            )
        parts = key[10:].split(":")
        if len(parts) != 2:
            raise IntegratorError(f"cBioPortal: bad key {key!r}")
        study_id, gene = parts
        profile_id = f"{study_id}_mutations"
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    f"https://www.cbioportal.org/api/molecular-profiles/{profile_id}/mutations",
                    params={"projection": "DETAILED"},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"cBioPortal transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"cBioPortal HTTP {r.status_code}: {r.text}")
        muts = r.json()
        gene_muts = [
            m for m in muts if (m.get("gene") or {}).get("hugoGeneSymbol") == gene
        ]
        return {
            "study": study_id,
            "gene": gene,
            "total_mutations": len(gene_muts),
            "samples_with_mutation": len({m.get("sampleId") for m in gene_muts}),
        }
