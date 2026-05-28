"""Cancer-context generator (v2.5 compositional foundation — RFC 0001 §2.3).

v2.5 ships:
- 2 seed JSON files at references/cancer_contexts/ (HCC + NSCLC EGFR+)
- CancerContextGenerator(icdo3, force_refresh=False) → JSON
- Scaffold stub for any other cancer (M6 hooks up live KG queries)

Real KG queries (PrimeKG + OncoKB + NCCN + cBioPortal + CT.gov) are M6.
"""
from __future__ import annotations

from .generator import CancerContextGenerator

__all__ = ["CancerContextGenerator"]
