"""Test Level 0-4 permission classification. Spec §7 G8 / §17.1 fix-target."""
from opl_cancer.validators.permission_levels import (
    Level, classify, requires_risk_disclosure, requires_patient_acknowledgment,
)


def test_level_0_information_statement() -> None:
    assert classify(claim_layer="established", is_actionable=False, has_serious_risk=False, off_label_or_eap=False) == Level.L0_INFORMATION


def test_level_1_reasoning_synthesis() -> None:
    assert classify(claim_layer="established", is_actionable=True, has_serious_risk=False, off_label_or_eap=False) == Level.L1_REASONING


def test_level_2_recommendation_within_evidence() -> None:
    assert classify(claim_layer="exploratory", is_actionable=True, has_serious_risk=False, off_label_or_eap=False) == Level.L2_RECOMMENDATION


def test_level_3_high_risk_advice() -> None:
    assert classify(claim_layer="exploratory", is_actionable=True, has_serious_risk=True, off_label_or_eap=False) == Level.L3_HIGH_RISK


def test_level_4_off_label_or_eap() -> None:
    assert classify(claim_layer="exploratory", is_actionable=True, has_serious_risk=True, off_label_or_eap=True) == Level.L4_BOUNDARY


def test_level_3_and_4_require_risk_disclosure() -> None:
    assert requires_risk_disclosure(Level.L3_HIGH_RISK)
    assert requires_risk_disclosure(Level.L4_BOUNDARY)
    assert not requires_risk_disclosure(Level.L0_INFORMATION)
    assert not requires_risk_disclosure(Level.L2_RECOMMENDATION)


def test_level_3_and_4_require_patient_ack() -> None:
    assert requires_patient_acknowledgment(Level.L3_HIGH_RISK)
    assert requires_patient_acknowledgment(Level.L4_BOUNDARY)
    assert not requires_patient_acknowledgment(Level.L1_REASONING)
