"""PubMed via NCBI E-utilities. Spec §2.5 F1."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from ._http import request_with_retry
from ._ncbi import with_ncbi_identity
from .base import Integrator, IntegratorError


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedIntegrator(Integrator):
    family = "F1"
    ttl_seconds = 7 * 24 * 3600  # spec §17.5 P2: PubMed 7-day TTL

    async def fetch(self, key: str) -> dict[str, Any]:
        if key.startswith("PMID:"):
            pmid = key[5:].strip()
            return await self._efetch(pmid)
        if key.startswith("search:"):
            term = key[7:].strip()
            return await self._esearch_then_efetch(term)
        raise IntegratorError(f"PubMed: unrecognised key prefix in {key!r}")

    async def _esearch_then_efetch(self, term: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/esearch.fcgi",
                    family="pubmed",
                    params=with_ncbi_identity({
                        "db": "pubmed",
                        "term": term,
                        "retmode": "json",
                        "retmax": 5,
                    }),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"PubMed esearch transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"PubMed esearch HTTP {r.status_code}: {r.text}")
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            raise IntegratorError(f"PubMed esearch empty for term {term!r}")
        return await self._efetch(ids[0])

    async def _efetch(self, pmid: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await request_with_retry(
                    http,
                    "GET",
                    f"{_BASE}/efetch.fcgi",
                    family="pubmed",
                    params=with_ncbi_identity({
                        "db": "pubmed",
                        "id": pmid,
                        "rettype": "abstract",
                        "retmode": "xml",
                    }),
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"PubMed efetch transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"PubMed efetch HTTP {r.status_code}: {r.text}")

        try:
            root = ET.fromstring(r.text)
            article = root.find(".//PubmedArticle")
            if article is None:
                raise IntegratorError(f"PubMed efetch: no PubmedArticle for PMID {pmid}")
            title_el = article.find(".//ArticleTitle")
            # Structured abstracts hold MULTIPLE <AbstractText> elements
            # (BACKGROUND / METHODS / RESULTS / CONCLUSIONS). The old
            # `.find(...).text` took only the first section — dropping RESULTS,
            # i.e. exactly the hazard ratios / median months / ORR a citation is
            # usually cited FOR. Concatenate every section (with its Label) and
            # use itertext() so nested markup (sup/sub/i) is captured. This is what
            # lets G36 see real entities and G56 verify a cited number is in-source.
            abstract_parts: list[str] = []
            for at in article.findall(".//Abstract/AbstractText"):
                label = (at.get("Label") or at.get("NlmCategory") or "").strip()
                body = "".join(at.itertext()).strip()
                if body:
                    abstract_parts.append(f"{label}: {body}" if label else body)
            journal_el = article.find(".//Journal/Title")
            return {
                "pmid": pmid,
                "title": "".join(title_el.itertext()).strip() if title_el is not None else "",
                "abstract": " ".join(abstract_parts),
                "journal": journal_el.text if journal_el is not None else "",
            }
        except ET.ParseError as e:
            raise IntegratorError(f"PubMed efetch XML parse: {e}") from e
