"""Production-grade validation stack (no-LLM gates + classifiers). Spec §2.6 + §7.

v2.5 adds the GateFamily framework — RFC 0001 §2.5. Existing 33 gates remain
fully functional; the family layer SITS ABOVE them.
"""
from __future__ import annotations

from .gate_families import (
    GateFamily,
    ProvenanceFamily,
    ReproducibilityFamily,
    SafetyDisclosureFamily,
    ScopeIsolationFamily,
    StatisticalValidityFamily,
    TemporalRecencyFamily,
    all_families,
    families_by_id,
    load_gates_registry,
)
from .mechanical_gates import all_gate_classes

__all__ = [
    "GateFamily",
    "ProvenanceFamily",
    "ReproducibilityFamily",
    "SafetyDisclosureFamily",
    "ScopeIsolationFamily",
    "StatisticalValidityFamily",
    "TemporalRecencyFamily",
    "all_families",
    "all_gate_classes",
    "families_by_id",
    "load_gates_registry",
]
