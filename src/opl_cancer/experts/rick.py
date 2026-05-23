"""Rick — Clinical Trial Specialist expert.

Plan refs: P1-T26.
Spec §2.2.X — Richard Schilsky archetype: cross-registry trial matching with
explicit inclusion+exclusion deltas, status filtering, EAP routing.

Behaviour inherited from LLMBackedExpert via prompts/experts/rick/persona.md
+ prompts/tasks/trial_matching.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class RickExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("trial_matching",)
    # F3 = ClinicalTrials.gov / ChiCTR / ISRCTN; F8 = NMPA EAP + FDA EAP.
    preferred_families: ClassVar[tuple[str, ...]] = ("F3", "F8")
