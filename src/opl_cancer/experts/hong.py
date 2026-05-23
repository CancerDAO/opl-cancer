"""Hong — TCM Oncology Adjuvant expert (NEVER replaces standard care).

Plan refs: P1-T26.
Spec §2.2.X — 林洪生 (Lin Hongsheng) archetype: TCM as adjuvant only, with
mandatory non_replacement_of_standard_care=true marker + drug-herb interaction
screen.

Founder-mode disclosure: every Hong output carries the
non_replacement_of_standard_care marker. The persona prompt enforces it; the
task prompt requires it as a JSON field.

Behaviour inherited from LLMBackedExpert via prompts/experts/hong/persona.md
+ prompts/tasks/tcm_oncology.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class HongExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("tcm_oncology",)
    # F1 = PubMed (limited high-quality TCM evidence; default to RCT / meta).
    preferred_families: ClassVar[tuple[str, ...]] = ("F1",)
