"""Aviv — Bioinformatician expert. P2-T4.

Archetype: Aviv Regev (single-cell, Broad). Portfolio centers on hypothesis
generation, pathway enrichment, single-cell re-analysis.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class AvivExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = (
        "hypothesis_generation",
        "pathway_enrichment",
        "single_cell_reanalysis",
    )
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F4", "F6")
