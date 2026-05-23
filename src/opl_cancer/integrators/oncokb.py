"""OncoKB — variant clinical actionability. Spec §2.5 F4.

Key format: <GENE>:<protein_change>:<tumor_type> (e.g. EGFR:L858R:NSCLC).
Requires ONCOKB_API_KEY env var.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


class OncoKBIntegrator(Integrator):
    family = "F4"
    ttl_seconds = 7 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        api_key: str | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self.api_key = api_key or os.environ.get("ONCOKB_API_KEY", "")
        if not self.api_key:
            raise IntegratorError("OncoKB: ONCOKB_API_KEY env var required")

    async def fetch(self, key: str) -> dict[str, Any]:
        parts = key.split(":")
        if len(parts) != 3:
            raise IntegratorError(
                f"OncoKB: expected GENE:variant:tumor_type, got {key!r}"
            )
        gene, variant, tumor = parts
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    "https://www.oncokb.org/api/v1/annotate/mutations/byProteinChange",
                    params={
                        "hugoSymbol": gene,
                        "alteration": variant,
                        "tumorType": tumor,
                    },
                    headers=headers,
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"OncoKB transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"OncoKB HTTP {r.status_code}: {r.text}")
        body = r.json()
        return {
            "gene": gene,
            "variant": variant,
            "tumor_type": tumor,
            "oncogenic": body.get("oncogenic", ""),
            "highest_level": body.get("highestSensitiveLevel", ""),
            "treatments": [
                {"drug": d.get("drugName", ""), "level": t.get("level", "")}
                for t in body.get("treatments", [])
                for d in t.get("drugs", [])
            ],
        }
