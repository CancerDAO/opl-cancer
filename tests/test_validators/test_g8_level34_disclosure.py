"""Test G8 Level-3/4 disclosure-card requirement."""
from opl_cancer.validators.gates.g8_level34_disclosure import G8Level34DisclosureGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g8_skip_level_2() -> None:
    gate = G8Level34DisclosureGate()
    r = gate.check({"permission_level": 2})
    assert r.status == GateStatus.SKIP


def test_g8_pass_level3_with_card() -> None:
    gate = G8Level34DisclosureGate()
    claim = {
        "permission_level": 3,
        "risk_disclosure_card": {"risks": ["nausea"], "watchdog_signs": ["fever > 38.5"]},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g8_fail_level3_missing_card() -> None:
    gate = G8Level34DisclosureGate()
    r = gate.check({"permission_level": 3})
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g8_fail_level4_missing_alternatives() -> None:
    gate = G8Level34DisclosureGate()
    claim = {
        "permission_level": 4,
        "risk_disclosure_card": {
            "risks": ["severe neutropenia"],
            "benefits": ["mPFS gain"],
            "watchdog_signs": ["ANC < 0.5"],
            # missing alternatives
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert "alternatives" in r.message
