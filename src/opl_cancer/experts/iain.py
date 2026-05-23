"""Iain — Meta-Analyst expert. P2-T3.

Archetype: Iain Chalmers (Cochrane founder). Portfolio focuses on meta-analysis,
cross-source consistency, and heterogeneity assessment.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class IainExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("meta_analysis", "cross_source_consistency")
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F2", "F4")
