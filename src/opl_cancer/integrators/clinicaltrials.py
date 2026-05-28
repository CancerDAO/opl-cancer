"""ClinicalTrials.gov v2 API. Spec §2.5 F3.

v2.1 P0-#8: ``verify_site_open(nct_id, site_name)`` cross-verifies a CT.gov
trial's RECRUITING status against the hospital's own site page. Rick
downgrades the trial card when verification != ``verified_open``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

from ._abc import IntegratorABC
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


class ClinicalTrialsGovIntegrator(Integrator, IntegratorABC):
    """v2.5 RFC 0001 §2.4 — first proof-of-protocol multi-inheritor.

    Inherits both:
    - v2.4 ``Integrator`` (cached fetch + TTL + family) — unchanged behaviour
    - v2.5 ``IntegratorABC`` (query / normalize / provenance protocol)
    """

    family = "F3"
    ttl_seconds = 24 * 3600  # spec §17.5 P2: CT.gov 1-day TTL
    id = "clinicaltrials"  # v2.5 entry-point name

    # ─── v2.5 IntegratorABC ────────────────────────────────────────────
    def query(self, key: str) -> Any:
        """Delegate to the (async) fetch chain; sync callers can `asyncio.run`."""
        import anyio

        return anyio.run(self.fetch, key)

    def normalize(self, raw: Any) -> dict[str, Any]:
        """CT.gov flat dict — already normalized by ``_flatten``."""
        if isinstance(raw, dict):
            return raw
        return {"value": raw}

    def provenance(self) -> dict[str, Any]:
        return {
            "integrator": "clinicaltrials.gov",
            "endpoint": _BASE,
            "family": self.family,
            "ttl_seconds": self.ttl_seconds,
            "version": "v2",
        }

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


# ─── v2.1 P0-#8: site cross-verification ─────────────────────────────────

_SITE_MAP_PATH = Path(__file__).parent / "site_verification_map.yaml"

with _SITE_MAP_PATH.open() as _f:
    _SITE_MAP: dict[str, dict[str, str]] = yaml.safe_load(_f).get("sites", {})


def _fetch_hospital_trial_page(url: str) -> str | None:
    """Fetch a hospital's own trial-status page. Returns the response body
    or None on transport failure / non-200 status.

    Patched in unit tests; the live path is invoked from Rick's
    ``trial_matching`` post-processing (glue/wave1_runner.py).
    """
    try:
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
    except (httpx.HTTPError, OSError):
        return None
    if r.status_code != 200:
        return None
    return r.text


def verify_site_open(nct_id: str, site_name: str) -> dict[str, Any]:
    """Cross-verify a CT.gov site's RECRUITING status against the hospital's
    own page.

    Returns one of:

      * ``{"status": "verified_open", "source": URL}`` — hospital page
        marks the trial as actively recruiting.
      * ``{"status": "verified_closed", "source": URL}`` — hospital page
        marks the trial as closed / completed.
      * ``{"status": "unverified", "reason": ..., ...}`` — hospital not in
        site map, fetch failed, or no clear marker present.

    Rick (trial_matching) downgrades the trial card's ranking when the
    return is anything other than ``verified_open``.
    """
    site_cfg = _SITE_MAP.get(site_name)
    if not site_cfg:
        return {
            "status": "unverified",
            "reason": "hospital_not_in_map",
            "site": site_name,
        }

    url = site_cfg["search"].format(nct_id=nct_id)
    body = _fetch_hospital_trial_page(url)
    if not body:
        return {"status": "unverified", "reason": "fetch_failed", "source": url}

    body_lower = body.lower()
    open_markers = ("actively recruiting", "招募中", "开放招募", "正在招募", "recruiting")
    closed_markers = ("closed", "completed", "停止招募", "已结束", "已完成")
    if any(m in body_lower for m in open_markers):
        return {"status": "verified_open", "source": url}
    if any(m in body_lower for m in closed_markers):
        return {"status": "verified_closed", "source": url}
    return {"status": "unverified", "reason": "no_status_marker", "source": url}
