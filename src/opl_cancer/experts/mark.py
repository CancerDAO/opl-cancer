"""Mark — Endocrinologist (irAE) expert. P4.5-T2.

Archetype: composite (ASCO + ESMO ICI irAE consensus methodology — not a real-person impersonation)
(thyroiditis / hypophysitis / T1DM emergent). Portfolio focuses on CTCAE-graded
endocrine irAE, corticosteroid algorithm, lifelong replacement framing.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class MarkExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("ici_endocrine_irae",)
    preferred_families: ClassVar[tuple[str, ...]] = ("F1",)
