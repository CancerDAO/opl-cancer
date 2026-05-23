"""ClinicalTrials.gov v2 API. Spec §2.5 F3."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_BASE = "https://clinicaltrials.gov/api/v2/studies"


def _flatten(study: dict[str, Any]) -> dict[str, Any]:
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    cond = p.get("conditionsModule", {})
    arms = p.get("armsInterventionsModule", {})
    elig = p.get("eligibilityModule", {})
    return {
        "nct_id": ident.get("nctId", ""),
        "title": ident.get("briefTitle", ""),
        "status": status.get("overallStatus", ""),
        "conditions": cond.get("conditions", []),
        "interventions": [iv.get("name", "") for iv in arms.get("interventions", [])],
        "eligibility": elig.get("eligibilityCriteria", ""),
    }


class ClinicalTrialsGovIntegrator(Integrator):
    family = "F3"
    ttl_seconds = 24 * 3600  # spec §17.5 P2: CT.gov 1-day TTL

    async def fetch(self, key: str) -> dict[str, Any]:
        if key.startswith("NCT:"):
            nct = key[4:].strip()
            try:
                async with httpx.AsyncClient(timeout=30.0) as http:
                    r = await http.get(f"{_BASE}/{nct}")
            except (httpx.HTTPError, ConnectionError, OSError) as e:
                raise IntegratorError(f"CT.gov transport: {e}") from e
            if r.status_code >= 400:
                raise IntegratorError(f"CT.gov HTTP {r.status_code}: {r.text}")
            return _flatten(r.json())
        if key.startswith("search:"):
            term = key[7:].strip()
            try:
                async with httpx.AsyncClient(timeout=30.0) as http:
                    r = await http.get(_BASE, params={
                        "query.term": term,
                        "filter.overallStatus": "RECRUITING",
                        "pageSize": 10,
                    })
            except (httpx.HTTPError, ConnectionError, OSError) as e:
                raise IntegratorError(f"CT.gov transport: {e}") from e
            if r.status_code >= 400:
                raise IntegratorError(f"CT.gov HTTP {r.status_code}: {r.text}")
            studies = [_flatten(s) for s in r.json().get("studies", [])]
            return {"query": term, "studies": studies}
        raise IntegratorError(f"CT.gov: bad key {key!r}")
