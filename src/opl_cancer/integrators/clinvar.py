"""ClinVar via NCBI E-utilities. Spec §2.5 F4."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class ClinVarIntegrator(Integrator):
    family = "F4"
    ttl_seconds = 30 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("variant:"):
            raise IntegratorError(f"ClinVar: expected variant:<term>, got {key!r}")
        term = key[8:].strip()
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r1 = await http.get(
                    f"{_BASE}/esearch.fcgi",
                    params={
                        "db": "clinvar",
                        "term": term,
                        "retmode": "json",
                        "retmax": 1,
                    },
                )
                if r1.status_code >= 400:
                    raise IntegratorError(f"ClinVar esearch HTTP {r1.status_code}")
                ids = r1.json().get("esearchresult", {}).get("idlist", [])
                if not ids:
                    raise IntegratorError(f"ClinVar: no records for {term!r}")
                uid = ids[0]
                r2 = await http.get(
                    f"{_BASE}/esummary.fcgi",
                    params={"db": "clinvar", "id": uid, "retmode": "json"},
                )
                if r2.status_code >= 400:
                    raise IntegratorError(f"ClinVar esummary HTTP {r2.status_code}")
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"ClinVar transport: {e}") from e

        summary = r2.json().get("result", {}).get(uid, {})
        return {
            "uid": uid,
            "title": summary.get("title", ""),
            "significance": (summary.get("clinical_significance") or {}).get(
                "description", ""
            ),
            "conditions": [
                t.get("trait_name", "") for t in summary.get("trait_set", [])
            ],
        }
