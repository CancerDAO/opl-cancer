"""G39 — biomarker_contingency unit tests.

Replays cross-model Finding 1 (CRITICAL) from session 0d1017d4 (KRAS-G12C/MSS
mCRC): a headline anti-EGFR regimen gated on an UNTESTED NRAS/BRAF biomarker.

Imports the gate module DIRECTLY (not via the package __init__) so the test
runs before the orchestrator registers the gate in gates/__init__.py.
"""
from __future__ import annotations

from opl_cancer.validators.gates.g39_biomarker_contingency import (
    G39BiomarkerContingencyGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G39BiomarkerContingencyGate()


# ── Finding-1 replay: headline anti-EGFR gated on UNTESTED NRAS/BRAF ─────────
FINDING_1_BLOCKING = {
    "claim_id": "c_finding1",
    "claim_text": "First recommendation: anti-EGFR (panitumumab)-based therapy.",
    "drugs_mentioned": ["panitumumab"],
    "regimen": {
        "is_headline": True,
        "rank": 1,
        "required_biomarkers": [
            {"gene": "RAS", "required_state": "wild-type", "patient_state": "wild-type"},
            # The buried, undeliverable dependency: NRAS/BRAF never tested.
            {"gene": "NRAS", "required_state": "wild-type", "patient_state": None},
            {"gene": "BRAF", "required_state": "wild-type", "patient_state": "unknown"},
        ],
    },
}

# Same regimen, but the producer correctly demoted it below a contingency
# banner because the biomarker is unresolved — legitimate, must PASS.
CONTINGENT_OPTION = {
    "claim_id": "c_contingent",
    "claim_text": "IF NRAS/BRAF wild-type is confirmed, consider anti-EGFR therapy.",
    "regimen": {
        "is_headline": False,
        "rank": 2,
        "required_biomarkers": [
            {"gene": "NRAS", "required_state": "wild-type", "patient_state": "untested"},
        ],
    },
}

# Clean headline: every required biomarker has a KNOWN, satisfying state.
CLEAN_HEADLINE = {
    "claim_id": "c_clean",
    "claim_text": "First recommendation: sotorasib (KRAS-G12C inhibitor).",
    "regimen": {
        "is_headline": True,
        "rank": 1,
        "required_biomarkers": [
            {"gene": "KRAS", "required_state": "G12C", "patient_state": "G12C"},
        ],
    },
}

# Headline with a KNOWN state that does NOT satisfy required_state — incoherent.
HEADLINE_STATE_MISMATCH = {
    "claim_id": "c_mismatch",
    "claim_text": "First recommendation: pembrolizumab (MSI-H gated).",
    "regimen": {
        "is_headline": True,
        "rank": 1,
        "required_biomarkers": [
            {"gene": "MSI", "required_state": "MSI-H", "patient_state": "MSS"},
        ],
    },
}

# Headline regimen with no biomarker dependency at all — PASS.
HEADLINE_NO_BIOMARKERS = {
    "claim_id": "c_nobm",
    "claim_text": "First recommendation: FOLFIRI.",
    "regimen": {"is_headline": True, "rank": 1},
}


def test_g39_fail_finding1_headline_on_unknown_biomarker() -> None:
    res = GATE.check(FINDING_1_BLOCKING)
    assert res.status == GateStatus.FAIL, res.message
    assert res.block is True
    # Both NRAS (null) and BRAF (unknown) should be flagged; RAS (satisfied) not.
    flagged = {v["gene"] for v in res.evidence["violations"]}
    assert flagged == {"NRAS", "BRAF"}, flagged


def test_g39_pass_contingent_option_on_unknown_biomarker() -> None:
    res = GATE.check(CONTINGENT_OPTION)
    assert res.status == GateStatus.PASS, res.message
    assert res.block is False


def test_g39_pass_clean_headline_known_satisfying_state() -> None:
    res = GATE.check(CLEAN_HEADLINE)
    assert res.status == GateStatus.PASS, res.message
    assert res.block is False


def test_g39_fail_headline_known_state_does_not_satisfy() -> None:
    res = GATE.check(HEADLINE_STATE_MISMATCH)
    assert res.status == GateStatus.FAIL, res.message
    assert res.block is True
    assert res.evidence["violations"][0]["reason"].startswith("known patient_state")


def test_g39_pass_headline_no_required_biomarkers() -> None:
    res = GATE.check(HEADLINE_NO_BIOMARKERS)
    assert res.status == GateStatus.PASS, res.message
    assert res.block is False


def test_g39_skip_when_no_regimen_field() -> None:
    res = GATE.check({"claim_id": "c_no_regimen", "claim_text": "TMB is a marker."})
    assert res.status == GateStatus.SKIP, res.message
    assert res.block is False


def test_g39_fail_rank1_treated_as_headline_without_is_headline() -> None:
    # is_headline unset but rank==1 → still headline per the schema contract.
    claim = {
        "claim_id": "c_rank1",
        "claim_text": "Anti-EGFR.",
        "regimen": {
            "rank": 1,
            "required_biomarkers": [
                {"gene": "NRAS", "required_state": "wild-type", "patient_state": ""},
            ],
        },
    }
    res = GATE.check(claim)
    assert res.status == GateStatus.FAIL, res.message
    assert res.block is True
