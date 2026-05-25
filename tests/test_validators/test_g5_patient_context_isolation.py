"""Test G5 patient-context-isolation gate."""
import pytest

from opl_cancer.validators.gates.g5_patient_context_isolation import (
    CrossPatientContaminationError,
    G5PatientContextIsolationGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g5_pass_matching_patient() -> None:
    gate = G5PatientContextIsolationGate()
    claim = {"patient_code": "p001", "run_id": "p001__mtb__2026-05-25T00:00:00Z"}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g5_fail_cross_patient() -> None:
    gate = G5PatientContextIsolationGate()
    claim = {"patient_code": "p001", "run_id": "p002__mtb__2026-05-25T00:00:00Z"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "cross-patient" in r.message


def test_g5_raise_when_configured() -> None:
    gate = G5PatientContextIsolationGate(raise_on_violation=True)
    with pytest.raises(CrossPatientContaminationError):
        gate.check(
            {"patient_code": "p001", "run_id": "p002__mtb__2026-05-25T00:00:00Z"}
        )


def test_g5_skip_when_run_id_missing() -> None:
    gate = G5PatientContextIsolationGate()
    r = gate.check({"patient_code": "p001"})
    assert r.status == GateStatus.SKIP
