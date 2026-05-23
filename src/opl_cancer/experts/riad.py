"""Riad — Interventional Oncologist expert. P4-T4.

Archetype: Riad Salem (Northwestern — HCC TARE/Y90). Portfolio focuses on
locoregional therapy: TACE, RFA, Y90, biliary/vascular stents.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class RiadExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("interventional_oncology",)
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F2")
