"""Level 0-4 permission classification. Spec §7 G8, §17.1 fix-target.

Founder-mode philosophy: levels do NOT gate external approval. They determine
which transparency / acknowledgment mechanism the patient sees (spec §8).
"""
from __future__ import annotations

from enum import IntEnum


class Level(IntEnum):
    L0_INFORMATION = 0
    L1_REASONING = 1
    L2_RECOMMENDATION = 2
    L3_HIGH_RISK = 3
    L4_BOUNDARY = 4


def classify(*, claim_layer: str, is_actionable: bool, has_serious_risk: bool, off_label_or_eap: bool) -> Level:
    """Classify a claim into Level 0-4. Spec §7 G8."""
    if off_label_or_eap:
        return Level.L4_BOUNDARY
    if has_serious_risk:
        return Level.L3_HIGH_RISK
    if claim_layer in ("exploratory", "speculative") and is_actionable:
        return Level.L2_RECOMMENDATION
    if is_actionable:
        return Level.L1_REASONING
    return Level.L0_INFORMATION


def requires_risk_disclosure(level: Level) -> bool:
    """Spec §7 G8: L3/L4 require risk-disclosure-card before render."""
    return level >= Level.L3_HIGH_RISK


def requires_patient_acknowledgment(level: Level) -> bool:
    """Spec §8 layer 4: L3/L4 require patient ack loop."""
    return level >= Level.L3_HIGH_RISK
