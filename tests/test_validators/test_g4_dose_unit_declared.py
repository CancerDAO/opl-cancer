"""Test G4 dose-unit-declared gate."""
from opl_cancer.validators.gates.g4_dose_unit_declared import G4DoseUnitDeclaredGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g4_pass_unit_and_freq() -> None:
    gate = G4DoseUnitDeclaredGate()
    claim = {"doses": [{"text": "cefepime 2 g IV q8h"}]}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g4_fail_missing_frequency() -> None:
    gate = G4DoseUnitDeclaredGate()
    claim = {"doses": ["paclitaxel 175 mg/m²"]}  # no frequency
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g4_fail_missing_unit() -> None:
    gate = G4DoseUnitDeclaredGate()
    claim = {"doses": ["give 10 cefepime qd"]}  # no recognised unit
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g4_skip_no_doses() -> None:
    gate = G4DoseUnitDeclaredGate()
    r = gate.check({"evidence": []})
    assert r.status == GateStatus.SKIP


def test_g4_nested_symptom_plan() -> None:
    gate = G4DoseUnitDeclaredGate()
    claim = {"symptom_plan": [{"symptom": "fever", "dose": "ibuprofen 400 mg qid"}]}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
