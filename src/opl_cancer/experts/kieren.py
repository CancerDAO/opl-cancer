"""Kieren — Infectious Disease expert. P4.5-T1.

Archetype: Kieren Marr (Johns Hopkins — neutropenic fever / invasive fungal
infection in cancer patients). Portfolio focuses on neutropenic fever
risk-stratification (MASCC), IDSA empiric antibiotic selection, fungal
coverage triggers, antibiotic stewardship in oncology.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class KierenExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("neutropenic_fever_management",)
    # F1 PubMed; F8 NCCN supportive-care.
    preferred_families: ClassVar[tuple[str, ...]] = ("F1", "F8")
