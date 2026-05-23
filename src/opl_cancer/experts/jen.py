"""Jen — Palliative Specialist expert. P4-T5.

Archetype: Jennifer Temel (MGH — NEJM 2010 early palliative care + OS benefit).
Portfolio focuses on symptom assessment (ESAS), QoL, opioid titration, goals of care.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class JenExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("palliative_symptom_qol",)
    preferred_families: ClassVar[tuple[str, ...]] = ("F1",)
