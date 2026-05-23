"""Tyler — Wet-Lab Designer expert. P3-T6.

Archetype: Tyler Jacks (MIT — engineered mouse cancer models). Portfolio focuses
on in-silico experimental design + minimal wet-lab validation steps that turn
Wave-2 hypotheses into testable propositions.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class TylerExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = (
        "hypothesis_validation",
        "in_silico_experiment_design",
    )
    preferred_families: ClassVar[tuple[str, ...]] = ("F6", "F7")
