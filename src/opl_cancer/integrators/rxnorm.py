"""RxNorm canonical drug name lookup. Spec §7 G3 / §2.5 F10."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_BASE = "https://rxnav.nlm.nih.gov/REST"


class RxNormIntegrator(Integrator):
    family = "F10"
    ttl_seconds = 90 * 24 * 3600  # static-ish drug naming

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("brand:"):
            raise IntegratorError(f"RxNorm: expected brand:<name>, got {key!r}")
        name = key[6:].strip()
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r1 = await http.get(f"{_BASE}/rxcui.json", params={"name": name})
                if r1.status_code >= 400:
                    raise IntegratorError(f"RxNorm rxcui HTTP {r1.status_code}")
                ids = (r1.json().get("idGroup") or {}).get("rxnormId") or []
                if not ids:
                    raise IntegratorError(f"RxNorm: no rxcui for {name!r}")
                rxcui = ids[0]
                r2 = await http.get(
                    f"{_BASE}/rxcui/{rxcui}/property.json",
                    params={"propName": "RxNorm Name"},
                )
                if r2.status_code >= 400:
                    raise IntegratorError(f"RxNorm property HTTP {r2.status_code}")
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"RxNorm transport: {e}") from e

        props = (r2.json().get("propConceptGroup") or {}).get("propConcept") or []
        generic = next(
            (p["propValue"] for p in props if p.get("propName") == "RxNorm Name"), ""
        )
        if not generic:
            raise IntegratorError(f"RxNorm: no RxNorm Name property for {name!r}")
        return {"brand": name, "rxcui": rxcui, "generic": generic}
