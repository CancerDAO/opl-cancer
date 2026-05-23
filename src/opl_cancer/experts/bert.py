"""Bert — Molecular Geneticist expert.

Plan refs: P1-T26.
Spec §2.2.X — Bert Vogelstein archetype: variant prioritisation, actionability,
co-alterations, germline pathogenicity, three-tier labelled.

Behaviour inherited from LLMBackedExpert via prompts/experts/bert/persona.md
+ prompts/tasks/molecular_ngs_interpretation.md.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class BertExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("molecular_ngs_interpretation",)
    # F4 = OncoKB / CIViC / ClinVar / gnomAD; F5 = cBioPortal / GDC (cohort context).
    preferred_families: ClassVar[tuple[str, ...]] = ("F4", "F5")
