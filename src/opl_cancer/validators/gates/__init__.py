"""Concrete mechanical gates. Spec §7 (G1-G33).

Registered in `mechanical_gates.all_gate_classes()`:
- P0-3 fix (v2.1) bumped count from 23 → 27 by adding G21/G25/G26/G27.
- v2.2 ADR-0022 added G28 (absolute_date).
- v2.3 ADR-0023 adds G29-G33 (Wave 6 manuscript invariants).
"""
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
from .g21_quantitative_anchor import G21QuantitativeAnchorGate
from .g22_ddr_zygosity import G22DDRZygosityGate
from .g23_recency_band import G23RecencyBandGate
from .g24_crisis_detection import G24CrisisDetectionGate
from .g25_deferred_evidence_block import G25DeferredEvidenceBlockGate
from .g26_evidence_strength_ranking import G26EvidenceStrengthRankingGate
from .g27_privacy_scrub import G27PrivacyScrubGate, redact_text, scan_text
from .g28_absolute_date import G28AbsoluteDateGate
from .g29_manuscript_authorship_disclosed import G29ManuscriptAuthorshipDisclosedGate
from .g30_claim_pmid_anchored import G30ClaimPMIDAnchoredGate
from .g31_figure_reproducible import G31FigureReproducibleGate
from .g32_data_availability_declared import G32DataAvailabilityDeclaredGate
from .g33_n1_design_transparent import G33N1DesignTransparentGate
# v2.7.0 ADR-0026 — delivery-integrity + anti-fabrication + completeness gates.
from .g34_delivery_attestation import G34DeliveryAttestationGate
from .g35_clinical_fact_provenance import G35ClinicalFactProvenanceGate
from .g36_pmid_topic_relevance import G36PMIDTopicRelevanceGate
from .g37_service_completeness import G37ServiceCompletenessGate
# v2.7.1 ADR-0026 (P1) — reasoning-quality gates (G38 reserved: entity-attachment
# enforcement is now done in-line by G36, which fails CLOSED when a PMID-bearing
# claim has no upstream entities and none can be derived — see g36 docstring).
from .g39_biomarker_contingency import G39BiomarkerContingencyGate
from .g40_drug_comorbidity_safety import G40DrugComorbiditySafetyGate
from .g41_soc_completeness import G41SoCCompletenessGate
from .g42_tier_discipline import G42TierDisciplineGate
from .g43_epistemic_symmetry import G43EpistemicSymmetryGate

# v2.8 research-team iteration (ADR-0027+). New gates start at G45 (G44 is
# reserved for the in-flight feat/deterministic-retrieval-standardization
# branch; G38 reserved).
from .g45_world_unknown_comparator import G45WorldUnknownComparatorGate  # B1/ADR-0029
from .g46_soc_baseline_quantified import G46SoCBaselineQuantifiedGate  # B1/ADR-0029
from .g48_research_delta import G48ResearchDeltaGate  # A3/ADR-0028
from .g54_memory_ledger_written import G54MemoryLedgerWrittenGate  # A1/ADR-0027

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
    "G21QuantitativeAnchorGate",
    "G22DDRZygosityGate",
    "G23RecencyBandGate",
    "G24CrisisDetectionGate",
    "G25DeferredEvidenceBlockGate",
    "G26EvidenceStrengthRankingGate",
    "G27PrivacyScrubGate",
    "G28AbsoluteDateGate",
    "G29ManuscriptAuthorshipDisclosedGate",
    "G30ClaimPMIDAnchoredGate",
    "G31FigureReproducibleGate",
    "G32DataAvailabilityDeclaredGate",
    "G33N1DesignTransparentGate",
    "G34DeliveryAttestationGate",
    "G35ClinicalFactProvenanceGate",
    "G36PMIDTopicRelevanceGate",
    "G37ServiceCompletenessGate",
    "G39BiomarkerContingencyGate",
    "G40DrugComorbiditySafetyGate",
    "G41SoCCompletenessGate",
    "G42TierDisciplineGate",
    "G43EpistemicSymmetryGate",
    "G45WorldUnknownComparatorGate",
    "G46SoCBaselineQuantifiedGate",
    "G48ResearchDeltaGate",
    "G54MemoryLedgerWrittenGate",
    "redact_text",
    "scan_text",
]
