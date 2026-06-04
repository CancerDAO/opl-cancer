"""NCBI SRA (Sequence Read Archive) integrator. Spec §2.5 F6, P3-T3.

Accession prefixes SRR/SRP/SRX/SRS. Uses eutils db=sra.
no-silent-fallback policy — raise on failure.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from ._http import request_with_retry
from ._ncbi import with_ncbi_identity
from .base import Integrator, IntegratorError

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_PREFIXES = ("SRR", "SRP", "SRX", "SRS", "ERR", "ERP", "ERX")


class SRAIntegrator(Integrator):
    family = "F6"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        accession = key.strip().upper()
        if not any(accession.startswith(p) for p in _PREFIXES):
            raise IntegratorError(
                f"SRA: unrecognised key {key!r}; expected SRR/SRP/SRX/SRS/ERR/ERP/ERX"
            )
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/esearch.fcgi",
                    family="sra",
                    params=with_ncbi_identity({
                        "db": "sra",
                        "term": accession,
                        "retmode": "json",
                    }),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"SRA esearch transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"SRA esearch HTTP {r.status_code}: {r.text}")
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            raise IntegratorError(f"SRA: accession {accession} not found")
        uid = ids[0]
        # efetch returns ExpXml-style XML
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r2 = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/efetch.fcgi",
                    family="sra",
                    params=with_ncbi_identity({"db": "sra", "id": uid, "rettype": "runinfo", "retmode": "csv"}),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"SRA efetch transport: {e}") from e
        if r2.status_code >= 400:
            raise IntegratorError(f"SRA efetch HTTP {r2.status_code}: {r2.text}")
        lines = r2.text.strip().splitlines()
        if len(lines) < 2:
            raise IntegratorError(f"SRA efetch empty CSV for {accession}")
        header = [h.strip() for h in lines[0].split(",")]
        first = [v.strip() for v in lines[1].split(",")]
        row = dict(zip(header, first, strict=False))
        return {
            "accession": accession,
            "uid": uid,
            "run": row.get("Run", ""),
            "experiment": row.get("Experiment", ""),
            "sample": row.get("Sample", ""),
            "study": row.get("BioProject", ""),
            "bases": row.get("bases", ""),
            "spots": row.get("spots", ""),
            "library_strategy": row.get("LibraryStrategy", ""),
            "library_layout": row.get("LibraryLayout", ""),
            "platform": row.get("Platform", ""),
            "raw": row,
        }

    # ET imported for forward compat parsing — silence ruff unused
    _ = ET
