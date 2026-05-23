"""Frances — Expanded Access Navigator expert. P4-T6.

Archetype: Frances Kelsey (FDA — drug-safety vigilance, ethics of access).
Portfolio focuses on NMPA/FDA Expanded Access Program (EAP) pathway eligibility,
sponsor/IRB chains, and L4-boundary risk framing.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class FrancesExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("expanded_access_navigation",)
    # F3 trials, F8 EAP-specific registry.
    preferred_families: ClassVar[tuple[str, ...]] = ("F3", "F8")
