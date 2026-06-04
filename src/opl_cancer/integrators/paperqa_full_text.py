"""PaperQA full-text fetch shim. v2.2 P1-#10 — F1 family.

Closes v2.1 P1-#10: Monte Carlo λ for ctDNA decay was labeled
"literature-informed" without an extracted citation. v2.2 records
parameter calibration provenance as one of:

  * paper_derived       — value extracted verbatim from full-text quote
  * informed_estimate   — value bounded by a literature range, exact
                          value not in source
  * literature_default  — fallback to a known canonical value with PMID

The integrator wraps NCBI's PMC OA full-text fetch (PMID → PMC full-text
URL via the ID-converter API). For unit tests the HTTP shim is patched.

Key format: ``pmid:<NNNNNNNN>``
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

import httpx

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


class CalibrationProvenance(str, Enum):
    PAPER_DERIVED = "paper_derived"
    INFORMED_ESTIMATE = "informed_estimate"
    LITERATURE_DEFAULT = "literature_default"


def classify_calibration_provenance(
    *,
    extracted_quote: str | None,
    was_from_full_text: bool,
    used_default: bool = False,
) -> CalibrationProvenance:
    """Classify a Monte Carlo / model parameter's provenance.

    A single canonical numeric value extracted verbatim → paper_derived.
    A range or bound extracted → informed_estimate.
    No extraction, fallback used → literature_default.
    """
    if was_from_full_text and extracted_quote:
        # A range or bound is informed_estimate; a single point value is
        # paper_derived. Heuristic: dash/range/CI indicates a range.
        if re.search(r"\d+\.?\d*\s*[-–]\s*\d+\.?\d*", extracted_quote) or \
           re.search(r"95% CI", extracted_quote, re.IGNORECASE) or \
           "range" in extracted_quote.lower():
            return CalibrationProvenance.INFORMED_ESTIMATE
        return CalibrationProvenance.PAPER_DERIVED
    if used_default:
        return CalibrationProvenance.LITERATURE_DEFAULT
    raise ValueError(
        "classify_calibration_provenance: need either a full-text extraction "
        "OR `used_default=True`. Cannot certify provenance otherwise."
    )


_ID_CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
_PMC_OA_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"


class PaperqaFullTextIntegrator(Integrator):
    """Wrap PMC OA full-text fetch for a PMID. Heavy on network; cache 24h."""

    family = "F1"  # same family as paperqa.py — interchangeable interpretation
    ttl_seconds = 24 * 3600

    def __init__(self, cache: IntegratorCache | None = None) -> None:
        super().__init__(cache=cache)

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("pmid:"):
            raise IntegratorError(
                f"PaperqaFullText: expected pmid:<NNNNNNNN>, got {key!r}"
            )
        pmid = key[len("pmid:"):].strip()
        if not pmid.isdigit():
            raise IntegratorError(
                f"PaperqaFullText: pmid must be numeric, got {pmid!r}"
            )
        return await self._fetch_pmc_full_text(pmid)

    async def _fetch_pmc_full_text(self, pmid: str) -> dict[str, Any]:
        # Real path: ID-converter → PMCID → /pmc/articles/<PMCID>/?format=ascii
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    _ID_CONVERTER_URL,
                    params={
                        "ids": pmid,
                        "format": "json",
                        "idtype": "pmid",
                    },
                )
                r.raise_for_status()
                body = r.json()
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(
                f"PaperqaFullText: ID-converter transport for PMID {pmid}: {e}. "
                "No silent fallback (no-silent-fallback policy)."
            ) from e
        records = body.get("records") or []
        if not records:
            raise IntegratorError(
                f"PaperqaFullText: no PMC record for PMID {pmid}"
            )
        pmcid = records[0].get("pmcid")
        if not pmcid:
            raise IntegratorError(
                f"PaperqaFullText: PMID {pmid} has no open-access PMC mirror "
                "(closed-access; full-text not retrievable via PMC OA API)"
            )
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                r = await http.get(_PMC_OA_URL.format(pmcid=pmcid))
                r.raise_for_status()
                full_text = r.text
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(
                f"PaperqaFullText: full-text transport for {pmcid}: {e}"
            ) from e
        return {
            "pmid": pmid,
            "pmcid": pmcid,
            "full_text": full_text,
            "source": "pmc_oa",
        }

    def extract_numeric_parameter(
        self, *, text: str, parameter_name: str
    ) -> dict[str, Any]:
        """Find `<param_name> = <number>` and return value + quote sentence.

        Returns {"value": float | None, "quote": str | None, "unit": str | None}.
        """
        # Locate `param_name = N` or `λ = N` or `param_name of N`
        # We also accept Greek letter lambda for the canonical ctDNA-decay case
        pname = re.escape(parameter_name)
        pattern = re.compile(
            rf"(?:{pname}|λ)\s*(?:=|of)\s*([0-9]+\.?[0-9]*)(?:\s*(/\s*\w+|per\s*\w+))?",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if not m:
            return {"value": None, "quote": None, "unit": None}
        value = float(m.group(1))
        unit = (m.group(2) or "").strip() or None
        # capture surrounding sentence for the quote
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 100)
        quote = text[start:end].strip()
        return {"value": value, "quote": quote, "unit": unit}


__all__ = [
    "PaperqaFullTextIntegrator",
    "CalibrationProvenance",
    "classify_calibration_provenance",
]
