"""Concrete mechanical gates. Spec §7 (G1-G24) + v1.5 epistemic gates (G25-G26)."""
from __future__ import annotations

from .g1_pmid_existence import G1PMIDExistenceGate
from .g2_pmid_quote_match import G2PMIDQuoteMatchGate
from .g3_drug_normalization import G3DrugNormalizationGate
from .g4_dose_unit_declared import G4DoseUnitDeclaredGate
from .g5_patient_context_isolation import (
    CrossPatientContaminationError,
    G5PatientContextIsolationGate,
)
from .g6_injection_scan import G6InjectionScanGate
from .g7_imperative_detector import G7ImperativeDetectorGate
from .g8_level34_disclosure import G8Level34DisclosureGate
from .g9_retraction_check import G9RetractionCheckGate
from .g10_guideline_version import G10GuidelineVersionGate
from .g11_no_silent_fallback import G11NoSilentFallbackGate
from .g12_memory_overflow import G12MemoryOverflowGate
from .g13_reviewer_model_distinct import G13ReviewerModelDistinctGate
from .g14_dataset_patient_match import G14DatasetPatientMatchGate
from .g15_multiple_testing_correction import G15MultipleTestingCorrectionGate
from .g16_batch_effect_declared import G16BatchEffectDeclaredGate
from .g17_meta_i2_policy import G17MetaI2PolicyGate
from .g18_meta_search_strategy import G18MetaSearchStrategyGate
from .g19_pi_imperative_detector import G19PIImperativeDetectorGate
from .g20_pi_disagreement_surfacing import G20PIDisagreementSurfacingGate
from .g22_ddr_zygosity import G22DDRZygosityGate
from .g23_recency_band import G23RecencyBandGate
from .g24_crisis_detection import G24CrisisDetectionGate
from .g25_deferred_evidence_block import G25DeferredEvidenceBlockGate
from .g26_evidence_strength_ranking import G26EvidenceStrengthRankingGate
from .g27_privacy_scrub import G27PrivacyScrubGate, redact_text, scan_text

__all__ = [
    "CrossPatientContaminationError",
    "G1PMIDExistenceGate",
    "G2PMIDQuoteMatchGate",
    "G3DrugNormalizationGate",
    "G4DoseUnitDeclaredGate",
    "G5PatientContextIsolationGate",
    "G6InjectionScanGate",
    "G7ImperativeDetectorGate",
    "G8Level34DisclosureGate",
    "G9RetractionCheckGate",
    "G10GuidelineVersionGate",
    "G11NoSilentFallbackGate",
    "G12MemoryOverflowGate",
    "G13ReviewerModelDistinctGate",
    "G14DatasetPatientMatchGate",
    "G15MultipleTestingCorrectionGate",
    "G16BatchEffectDeclaredGate",
    "G17MetaI2PolicyGate",
    "G18MetaSearchStrategyGate",
    "G19PIImperativeDetectorGate",
    "G20PIDisagreementSurfacingGate",
    "G22DDRZygosityGate",
    "G23RecencyBandGate",
    "G24CrisisDetectionGate",
    "G25DeferredEvidenceBlockGate",
    "G26EvidenceStrengthRankingGate",
    "G27PrivacyScrubGate",
    "redact_text",
    "scan_text",
]
