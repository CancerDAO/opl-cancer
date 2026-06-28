"""Mechanical gate framework — no-LLM hard rules. Spec §7.

P0 ships only the framework (Gate abstract base + run_gates dispatcher).
Concrete gates G1-G33 are implemented in P5 / v1.3.1 / v1.3.2 / v1.5 /
v2.2 / v2.3 and registered via ``all_gate_classes()`` below so callers
can introspect/instantiate the full set without re-import-listing every
module.

History: through v1.5.5 only G1-G20 + G22-G24 were registered (23 gates)
while G21/G25/G26/G27 were defined and re-exported but never picked up by
the orchestrator loop. The P0-3 fix (v2.1) registered all 27.
v2.2 adds G28 absolute_date (P1-#15) — closes the LLM-confused-
weeks-for-months failure mode (ADR-0022).
v2.3 adds G29-G33 (ADR-0023) for Wave 6 manuscript invariants:
  G29 manuscript_authorship_disclosed
  G30 claim_pmid_anchored
  G31 figure_reproducible
  G32 data_availability_declared
  G33 n1_design_transparent
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
    """Return the full G1-G33 gate-class registry.

    Wrapped in a function to defer the import-cycle: ``mechanical_gates`` is
    imported by every concrete gate module, so we cannot import the gates at
    top-level here. Call this at orchestrator-bootstrap time.

    Order is canonical (G1 → G33) to match spec §7 + ADR-0022 + ADR-0023
    numbering. G24 (crisis_detection) is the SAFETY floor — keyword-scan
    no-LLM gate that locks Wave runners on SI / self-harm language
    (v1.3.2 hot-fix). G21 / G25-G27 added to registry in P0-3 (previously
    defined but unhooked). G28 (absolute_date) added in v2.2 — closes the
    LLM "5 weeks → 5 months" failure mode (P1-#15, ADR-0022). G29-G33
    added in v2.3 (ADR-0023) for Wave 6 manuscript invariants.
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
        G21QuantitativeAnchorGate,
        G22DDRZygosityGate,
        G23RecencyBandGate,
        G24CrisisDetectionGate,
        G25DeferredEvidenceBlockGate,
        G26EvidenceStrengthRankingGate,
        G27PrivacyScrubGate,
        G28AbsoluteDateGate,
        G29ManuscriptAuthorshipDisclosedGate,
        G30ClaimPMIDAnchoredGate,
        G31FigureReproducibleGate,
        G32DataAvailabilityDeclaredGate,
        G33N1DesignTransparentGate,
        # v2.7.0 ADR-0026 — delivery-integrity + anti-fabrication + completeness.
        G34DeliveryAttestationGate,
        G35ClinicalFactProvenanceGate,
        G36PMIDTopicRelevanceGate,
        G37ServiceCompletenessGate,
        # v2.7.1 ADR-0026 (P1) — reasoning-quality gates (G38 reserved; entity-
        # attachment enforcement is in-line in G36, which fails closed).
        G39BiomarkerContingencyGate,
        G40DrugComorbiditySafetyGate,
        G41SoCCompletenessGate,
        G42TierDisciplineGate,
        G43EpistemicSymmetryGate,
        # v2.8 research-team iteration (ADR-0027+). G44 reserved for the
        # in-flight retrieval-standardization branch; remaining gates land with
        # their respective items. Canonical (ascending) order.
        G45WorldUnknownComparatorGate,  # B1/ADR-0029
        G46SoCBaselineQuantifiedGate,  # B1/ADR-0029
        G47SourceSectionDepthGate,  # B2/ADR-0030
        G48ResearchDeltaGate,  # A3/ADR-0028
        G49ForecastPreRegistrationGate,  # C2/ADR-0032
        G52FailureLedgerGate,  # C3/ADR-0033
        G54MemoryLedgerWrittenGate,  # A1/ADR-0027
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
        G21QuantitativeAnchorGate,
        G22DDRZygosityGate,
        G23RecencyBandGate,
        G24CrisisDetectionGate,
        G25DeferredEvidenceBlockGate,
        G26EvidenceStrengthRankingGate,
        G27PrivacyScrubGate,
        G28AbsoluteDateGate,
        G29ManuscriptAuthorshipDisclosedGate,
        G30ClaimPMIDAnchoredGate,
        G31FigureReproducibleGate,
        G32DataAvailabilityDeclaredGate,
        G33N1DesignTransparentGate,
        G34DeliveryAttestationGate,
        G35ClinicalFactProvenanceGate,
        G36PMIDTopicRelevanceGate,
        G37ServiceCompletenessGate,
        G39BiomarkerContingencyGate,
        G40DrugComorbiditySafetyGate,
        G41SoCCompletenessGate,
        G42TierDisciplineGate,
        G43EpistemicSymmetryGate,
        G45WorldUnknownComparatorGate,
        G46SoCBaselineQuantifiedGate,
        G47SourceSectionDepthGate,
        G48ResearchDeltaGate,
        G49ForecastPreRegistrationGate,
        G52FailureLedgerGate,
        G54MemoryLedgerWrittenGate,
    ]
