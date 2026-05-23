"""Steve — Nutritionist expert. P4-T7.

Archetype: Stephen Heber (UCLA Center for Human Nutrition). Portfolio focuses
on PG-SGA assessment, cachexia staging, energy/protein targets, supplement-drug
interaction checks.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class SteveExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("oncology_nutrition",)
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F2")
