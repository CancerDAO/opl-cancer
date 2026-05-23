"""gnomAD allele frequency lookup. Spec §2.5 F4."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_QUERY = """
query($variant_id: String!, $dataset: DatasetId!) {
  variant(variantId: $variant_id, dataset: $dataset) {
    variant_id
    exome { af ac an }
    genome { af ac an }
  }
}
"""


class GnomADIntegrator(Integrator):
    family = "F4"
    ttl_seconds = 90 * 24 * 3600  # gnomAD releases are infrequent

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("variant:"):
            raise IntegratorError(
                f"gnomAD: expected variant:<chr-pos-ref-alt>:<build>, got {key!r}"
            )
        rest = key[8:].strip()
        try:
            variant_id, build = rest.rsplit(":", 1)
        except ValueError as e:
            raise IntegratorError(f"gnomAD: bad key format {key!r}") from e
        dataset = "gnomad_r4" if build.upper() == "GRCH38" else "gnomad_r2_1"
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.post(
                    "https://gnomad.broadinstitute.org/api",
                    json={
                        "query": _QUERY,
                        "variables": {"variant_id": variant_id, "dataset": dataset},
                    },
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"gnomAD transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"gnomAD HTTP {r.status_code}: {r.text}")
        body = r.json()
        if "errors" in body:
            raise IntegratorError(f"gnomAD GraphQL: {body['errors']}")
        v = (body.get("data") or {}).get("variant")
        if v is None:
            raise IntegratorError(f"gnomAD: variant {variant_id} not in {dataset}")
        exome = v.get("exome") or {}
        return {
            "variant_id": v.get("variant_id", variant_id),
            "dataset": dataset,
            "af": exome.get("af"),
            "allele_count": exome.get("ac"),
            "allele_number": exome.get("an"),
        }
