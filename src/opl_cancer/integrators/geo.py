"""NCBI GEO (Gene Expression Omnibus) integrator. Spec §2.5 F6, P3-T1.

Accession prefixes (GSE/GDS/GPL/GSM) or ``search:<term>`` for ESearch.
Uses NCBI eutils db=gds. no-silent-fallback policy — raise on transport failure.
"""
from __future__ import annotations

from typing import Any

import httpx

from ._http import request_with_retry
from ._ncbi import with_ncbi_identity
from .base import Integrator, IntegratorError

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ACCESSION_PREFIXES = ("GSE", "GDS", "GPL", "GSM")


class GEOIntegrator(Integrator):
    family = "F6"
    ttl_seconds = 7 * 24 * 3600  # 7-day TTL (matches PubMed)

    async def fetch(self, key: str) -> dict[str, Any]:
        if key.startswith("search:"):
            term = key[7:].strip()
            return await self._esearch_then_summary(term)
        if any(key.upper().startswith(p) for p in _ACCESSION_PREFIXES):
            return await self._esummary_by_accession(key.upper())
        raise IntegratorError(
            f"GEO: unrecognised key {key!r}; expected GSE/GDS/GPL/GSM or search:<term>"
        )

    async def _esearch_then_summary(self, term: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/esearch.fcgi",
                    family="geo",
                    params=with_ncbi_identity({
                        "db": "gds",
                        "term": term,
                        "retmode": "json",
                        "retmax": 5,
                    }),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"GEO esearch transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"GEO esearch HTTP {r.status_code}: {r.text}")
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            raise IntegratorError(f"GEO esearch empty for term {term!r}")
        return await self._esummary(ids[0])

    async def _esummary_by_accession(self, accession: str) -> dict[str, Any]:
        # Use term-search to resolve accession -> uid first
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/esearch.fcgi",
                    family="geo",
                    params=with_ncbi_identity({
                        "db": "gds",
                        "term": f"{accession}[Accession]",
                        "retmode": "json",
                    }),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"GEO accession lookup transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(
                f"GEO accession lookup HTTP {r.status_code}: {r.text}"
            )
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            raise IntegratorError(f"GEO accession {accession} not found")
        return await self._esummary(ids[0])

    async def _esummary(self, uid: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/esummary.fcgi",
                    family="geo",
                    params=with_ncbi_identity({"db": "gds", "id": uid, "retmode": "json"}),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"GEO esummary transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"GEO esummary HTTP {r.status_code}: {r.text}")
        result = r.json().get("result", {})
        if uid not in result:
            raise IntegratorError(f"GEO esummary missing uid {uid}")
        entry = result[uid]
        return {
            "uid": uid,
            "accession": entry.get("accession", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "n_samples": entry.get("n_samples", 0),
            "gpl": entry.get("gpl", ""),
            "taxon": entry.get("taxon", ""),
            "raw": entry,
        }
