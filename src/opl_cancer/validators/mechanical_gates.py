"""Mechanical gate framework — no-LLM hard rules. Spec §7.

P0 ships only the framework (Gate abstract base + run_gates dispatcher).
Concrete gates G1-G24 are implemented in P5 / v1.3.1 / v1.3.2 and registered
via ``ALL_GATE_CLASSES`` below so callers can introspect/instantiate the full
set without re-import-listing every module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class GateResult(BaseModel):
    gate: str
    status: GateStatus
    message: str
    block: bool = False
    evidence: dict[str, Any] = {}


class Gate(ABC):
    """Abstract base for all mechanical gates. Subclass + override check()."""

    name: str
    description: str
    failure_mode_code: str

    @abstractmethod
    def check(self, claim: dict[str, Any]) -> GateResult:
        ...


def run_gates(claim: dict[str, Any], gates: list[Gate]) -> list[GateResult]:
    """Run gates in order. If a gate returns block=True, stop further checks."""
    results: list[GateResult] = []
    for gate in gates:
        r = gate.check(claim)
        results.append(r)
        if r.block:
            break
    return results


def all_gate_classes() -> list[type[Gate]]:
    """Return the full G1-G24 gate-class registry.

    Wrapped in a function to defer the import-cycle: ``mechanical_gates`` is
    imported by every concrete gate module, so we cannot import the gates at
    top-level here. Call this at orchestrator-bootstrap time.

    Order is canonical (G1 → G24) to match spec §7 numbering.
    G24 (crisis_detection) is the SAFETY floor — keyword-scan no-LLM gate
    that locks Wave runners on SI / self-harm language (v1.3.2 hot-fix).
    """
    from .gates import (  # noqa: PLC0415 — intentional lazy import
        G1PMIDExistenceGate,
        G2PMIDQuoteMatchGate,
        G3DrugNormalizationGate,
        G4DoseUnitDeclaredGate,
        G5PatientContextIsolationGate,
        G6InjectionScanGate,
        G7ImperativeDetectorGate,
        G8Level34DisclosureGate,
        G9RetractionCheckGate,
        G10GuidelineVersionGate,
        G11NoSilentFallbackGate,
        G12MemoryOverflowGate,
        G13ReviewerModelDistinctGate,
        G14DatasetPatientMatchGate,
        G15MultipleTestingCorrectionGate,
        G16BatchEffectDeclaredGate,
        G17MetaI2PolicyGate,
        G18MetaSearchStrategyGate,
        G19PIImperativeDetectorGate,
        G20PIDisagreementSurfacingGate,
        G22DDRZygosityGate,
        G23RecencyBandGate,
        G24CrisisDetectionGate,
    )

    return [
        G1PMIDExistenceGate,
        G2PMIDQuoteMatchGate,
        G3DrugNormalizationGate,
        G4DoseUnitDeclaredGate,
        G5PatientContextIsolationGate,
        G6InjectionScanGate,
        G7ImperativeDetectorGate,
        G8Level34DisclosureGate,
        G9RetractionCheckGate,
        G10GuidelineVersionGate,
        G11NoSilentFallbackGate,
        G12MemoryOverflowGate,
        G13ReviewerModelDistinctGate,
        G14DatasetPatientMatchGate,
        G15MultipleTestingCorrectionGate,
        G16BatchEffectDeclaredGate,
        G17MetaI2PolicyGate,
        G18MetaSearchStrategyGate,
        G19PIImperativeDetectorGate,
        G20PIDisagreementSurfacingGate,
        G22DDRZygosityGate,
        G23RecencyBandGate,
        G24CrisisDetectionGate,
    ]
