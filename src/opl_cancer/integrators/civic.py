"""CIViC clinical evidence grading via GraphQL. Spec §2.5 F4."""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_GRAPHQL = "https://civicdb.org/api/graphql"

_QUERY = """
query($gene: String!, $variant: String!) {
  variants(featureName: $gene, name: $variant, first: 5) {
    nodes {
      id name
      evidenceItems(first: 20) {
        nodes {
          id evidenceLevel evidenceDirection clinicalSignificance
          drugs { name }
          source { citationId }
        }
      }
    }
  }
}
"""


class CIViCIntegrator(Integrator):
    family = "F4"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if ":" not in key:
            raise IntegratorError(f"CIViC: expected GENE:variant, got {key!r}")
        gene, variant = key.split(":", 1)
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.post(
                    _GRAPHQL,
                    json={
                        "query": _QUERY,
                        "variables": {"gene": gene, "variant": variant},
                    },
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"CIViC transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"CIViC HTTP {r.status_code}: {r.text}")
        body = r.json()
        if "errors" in body:
            raise IntegratorError(f"CIViC GraphQL errors: {body['errors']}")
        nodes = body.get("data", {}).get("variants", {}).get("nodes", [])
        if not nodes:
            raise IntegratorError(f"CIViC: no variant found for {gene}:{variant}")
        v = nodes[0]
        return {
            "gene": gene,
            "variant": v.get("name", variant),
            "civic_variant_id": v.get("id"),
            "evidence_items": [
                {
                    "id": e.get("id"),
                    "level": e.get("evidenceLevel"),
                    "direction": e.get("evidenceDirection"),
                    "significance": e.get("clinicalSignificance"),
                    "drugs": [d.get("name", "") for d in e.get("drugs", [])],
                    "pmid": (e.get("source") or {}).get("citationId"),
                }
                for e in v.get("evidenceItems", {}).get("nodes", [])
            ],
        }
