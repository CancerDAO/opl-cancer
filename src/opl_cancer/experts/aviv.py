"""Aviv — Bioinformatician expert. P2-T4.

Archetype: Aviv Regev (single-cell, Broad). Portfolio centers on hypothesis
generation, pathway enrichment, single-cell re-analysis.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class AvivExpert(LLMBackedExpert):
    # P3-T7: extended portfolio with dataset_acquisition + bioinformatics_data_analysis;
    # preferred families add F7 (DepMap/CCLE).
    portfolio: ClassVar[tuple[str, ...]] = (
        "hypothesis_generation",
        "pathway_enrichment",
        "single_cell_reanalysis",
        "dataset_acquisition",
        "bioinformatics_data_analysis",
        "hypothesis_validation",  # Aviv can validate in-silico-only; Tyler preferred for wet-lab
    )
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F4", "F6", "F7")
