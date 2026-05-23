"""Mary — Pharmacologist (DDI / ADME / dosing) expert. P4-T2.

Archetype: Mary Relling (TPMT pharmacogenomics, St. Jude). Portfolio focuses on
drug-drug interaction screens, ADME implications, and dose adjustment.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class MaryExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("ddi_adme_dosing",)
    # F1 PubMed evidence; F10 RxNorm normalization.
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F10")
