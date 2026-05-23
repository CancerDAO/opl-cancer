"""Rosa — Surgical Pathologist expert.

Plan refs: P1-T26.
Spec §2.2.X — Juan Rosai archetype: histology + IHC interpretation, anchored
to pathology report wording, three-tier labelled.

The class is intentionally minimal: portfolio + preferred_families. All
behaviour (plan / execute / review / audit / integrate / feedback) is inherited
from LLMBackedExpert, which drives the LLM via prompts/experts/rosa/persona.md
+ prompts/tasks/pathology_interpretation.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class RosaExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("pathology_interpretation",)
    # F4 = CIViC / OncoKB — IHC marker → therapy linkage context.
    preferred_families: ClassVar[tuple[str, ...]] = ("F4",)
