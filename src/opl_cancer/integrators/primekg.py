"""PrimeKG integrator stub. v2.0.0.

PrimeKG (Harvard, Marinka Zitnik lab) — 129K nodes, 4M edges, 29 relation
types covering gene-gene, drug-drug, drug-disease, pathway, phenotype.
Repository: https://github.com/mims-harvard/PrimeKG

This is a STUB — it accepts a ``stub_response`` for tests and raises
``NotImplementedError`` for live queries until the real HTTP/SPARQL client
lands in ``iter/v2-followup-primekg``. Per ``no-silent-fallback policy``
this is acceptable for v2.0.0-rc1 because:

  (a) The stub is honest — it raises rather than silently returning empty.
  (b) The hypothesis_generation prompt accepts empty ``kg_evidence`` and
      routes to the non-KG-dependent strategies (literature_gap etc.).
  (c) Real PrimeKG client is a tracked follow-up
      (see ``references/v2-roadmap.md`` row ``iter/v2-followup-primekg``).

Maya is the primary consumer (target_synergy_emergent strategy).
"""
from __future__ import annotations

from typing import Any


class PrimeKGClient:
    """PrimeKG query client (stub for v2.0.0-rc1)."""

    def __init__(self, stub_response: dict[str, Any] | None = None) -> None:
        self._stub = stub_response

    async def query_synergy(
        self,
        *,
        gene_a: str,
        gene_b: str | None = None,
        relation_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        """Query gene-gene + drug-target synergy edges between two genes.

        Returns dict with shape ``{kg_source, kg_version, query, edges}``.
        """
        if self._stub is not None:
            return self._stub
        raise NotImplementedError(
            "PrimeKGClient.query_synergy live client not yet wired — tracked in "
            "iter/v2-followup-primekg. Pass stub_response= for tests."
        )

    async def query_synthetic_lethal(
        self,
        *,
        gene: str,
    ) -> dict[str, Any]:
        """Query synthetic-lethal partner candidates for a single gene.

        Returns dict with shape ``{kg_source, kg_version, query, partners}``.
        """
        if self._stub is not None:
            return self._stub
        raise NotImplementedError(
            "PrimeKGClient.query_synthetic_lethal live client not yet wired — "
            "tracked in iter/v2-followup-primekg."
        )
