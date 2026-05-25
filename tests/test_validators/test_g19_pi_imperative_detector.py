"""Test G19 PI-imperative detector."""
from opl_cancer.validators.gates.g19_pi_imperative_detector import (
    G19PIImperativeDetectorGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g19_skip_no_pi_fields() -> None:
    gate = G19PIImperativeDetectorGate()
    r = gate.check({"summary": "You must take this drug."})  # not a PI field
    assert r.status == GateStatus.SKIP


def test_g19_pass_clean_pi() -> None:
    gate = G19PIImperativeDetectorGate()
    claim = {
        "pi_delivery": {
            "patient_summary": "Your team has identified two options to discuss next week."
        }
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g19_fail_imperative_in_pi() -> None:
    gate = G19PIImperativeDetectorGate()
    claim = {"patient_brief": "You must start chemotherapy immediately."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g19_pass_imperative_with_evidence_and_risk() -> None:
    gate = G19PIImperativeDetectorGate()
    claim = {
        "patient_brief": (
            "You must start levothyroxine, but there is risk of adrenal crisis (PMID:99999)."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g19_fail_zh_imperative_in_pi() -> None:
    gate = G19PIImperativeDetectorGate()
    claim = {"patient_facing_summary": "应该立即停用免疫治疗。"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
