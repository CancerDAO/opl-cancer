"""Test G20 PI disagreement-surfacing gate."""
from opl_cancer.validators.gates.g20_pi_disagreement_surfacing import (
    G20PIDisagreementSurfacingGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g20_skip_no_disagreement() -> None:
    gate = G20PIDisagreementSurfacingGate()
    claim = {
        "reviewer": {"disagreement": {"confidence_delta": 0.1}},
        "pi_delivery": {"summary": "Plan A is recommended."},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP


def test_g20_pass_marker_present() -> None:
    gate = G20PIDisagreementSurfacingGate()
    claim = {
        "reviewer": {"disagreement": {"confidence_delta": 0.6}},
        "pi_delivery": {
            "summary": (
                "Plan A is one option. **Reviewer 在这一点上分歧了** and prefers Plan B."
            )
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g20_fail_marker_missing() -> None:
    gate = G20PIDisagreementSurfacingGate()
    claim = {
        "reviewer": {"disagreement": {"confidence_delta": 0.6}},
        "pi_delivery": {"summary": "Plan A is the recommendation."},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g20_fail_audit_flag_no_marker() -> None:
    gate = G20PIDisagreementSurfacingGate()
    claim = {
        "reviewer": {"audit_flag": "RED"},
        "pi_delivery": {"summary": "Plan A is fine."},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g20_fail_when_disagreement_but_no_pi() -> None:
    gate = G20PIDisagreementSurfacingGate()
    claim = {"reviewer": {"audit_flag": "YELLOW"}}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
