"""Ted — Radiation Oncologist expert. P4-T3.

Archetype: Theodore Lawrence (Michigan, GI radiotherapy). Portfolio focuses on
IMRT/SBRT/SRS planning, BED10 dose-fractionation, organ-at-risk (OAR) constraints.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class TedExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("radiation_planning",)
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F2")
