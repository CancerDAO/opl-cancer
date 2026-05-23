"""Vince — Treating Oncologist expert.

Plan refs: P1-T26.
Spec §2.2.X — Vincent DeVita archetype: treatment-line sequencing, regimen
options-with-trade-offs (never command form), guideline-anchored, three-tier
labelled.

Behaviour inherited from LLMBackedExpert via prompts/experts/vince/persona.md
+ prompts/tasks/treatment_line_recommendation.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class VinceExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("treatment_line_recommendation",)
    # F2 = NCCN/CSCO/ESMO guideline excerpts; F1 = PubMed for supporting evidence.
    preferred_families: ClassVar[tuple[str, ...]] = ("F2", "F1")
