"""Heddy — Radiologist expert (RECIST / iRECIST).

Plan refs: P1-T26.
Spec §2.2.X — Hedvig Hricak archetype: tumor measurement + RECIST 1.1 / iRECIST
response category, anchored to radiology-report wording.

P1 mode: TEXT-based — operates over radiology report text; no DICOM AI yet.

Behaviour inherited from LLMBackedExpert via prompts/experts/heddy/persona.md
+ prompts/tasks/recist_progression.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class HeddyExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("recist_progression",)
    # F1 = PubMed (RECIST methodology + iRECIST papers).
    preferred_families: ClassVar[tuple[str, ...]] = ("F1",)
