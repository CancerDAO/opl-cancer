"""Maya — Knowledge-Graph Synergy Reasoner expert. v2.0.0.

Composite archetype: Marinka Zitnik (PrimeKG, Harvard) + Tijana Milenković
(network medicine). Owns the ``target_synergy_emergent`` generation strategy.
Reads from PrimeKG / Open Targets / DepMap integrators to surface gene-gene,
drug-drug, and synthetic-lethal edges in THIS patient's molecular profile.

Part of v2 paradigm shift (ADR-0010).
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class MayaExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = (
        "target_synergy_emergent",
        "synthetic_lethal_partner_query",
        "drug_drug_synergy_kg_query",
        "pathway_crosstalk_reasoning",
    )
    preferred_families: ClassVar[tuple[str, ...]] = ("F4", "F6", "F7", "F9")
    persona_version: ClassVar[str] = "v2.0.0"
