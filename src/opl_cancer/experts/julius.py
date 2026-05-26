"""Julius — Medicinal Chemist (in silico) expert. v2.0.0.

Composite archetype: generative-chemistry research lineage (DiffDock / ESM /
RDKit / medchem filters). Owns the ``undrugged_target_design`` generation
strategy. Given an undrugged target X surfaced by Maya / Aviv, proposes
candidate molecular scaffolds with three-tier labels:
- ``[E]`` for the methodology (structure source, virtual screen, filters)
- ``[S]`` for the candidate molecule itself (must include testability_path)

v2.0.0: outputs are in-silico proposals only — wet-lab validation explicitly
delegated to Tyler. No prescriptive drug recommendation framing.

Part of v2 paradigm shift (ADR-0010).
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class JuliusExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = (
        "undrugged_target_design",
        "structure_source_acquisition",
        "virtual_screen_design",
        "chemical_filter_application",
    )
    preferred_families: ClassVar[tuple[str, ...]] = ("F4", "F7", "F11")
    persona_version: ClassVar[str] = "v2.0.0"
