"""Test G14 dataset-patient-match gate."""
from opl_cancer.validators.gates.g14_dataset_patient_match import (
    G14DatasetPatientMatchGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g14_pass_high_match() -> None:
    gate = G14DatasetPatientMatchGate(threshold=0.6)
    claim = {"dataset_acquisition": {"match_score": 0.82}}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g14_warn_low_match() -> None:
    gate = G14DatasetPatientMatchGate(threshold=0.6)
    claim = {"dataset_acquisition": {"match_score": 0.45}}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN, reviewer-reselect
    # v1.3.0 EVAL panel: action now includes "or widen caveats" branch since
    # weak conditional-axis matches can be retained with explicit caveats.
    assert r.evidence["reviewer_action"] == "reselect_dataset_or_widen_caveats"


def test_g14_warn_conditional_axis_low() -> None:
    """v1.3.0: conditional axes (ethnicity/metastatic_site/cns_involvement) fire WARN below floor."""
    gate = G14DatasetPatientMatchGate(threshold=0.6)
    claim = {"dataset_acquisition": {
        "match_score": 0.75,  # overall OK
        "ethnicity_score": 0.20,  # but cohort is wrong-ethnicity for this patient
    }}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert "ethnicity" in r.message


def test_g14_pass_conditional_axis_not_emitted() -> None:
    """Conditional axes are only enforced when the producer emits them.

    If `metastatic_site_score` is not emitted, G14 does not penalise — the
    patient profile may not carry that dimension.
    """
    gate = G14DatasetPatientMatchGate(threshold=0.6)
    claim = {"dataset_acquisition": {"match_score": 0.80}}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g14_block_missing_score() -> None:
    gate = G14DatasetPatientMatchGate()
    claim = {"dataset_acquisition": {"dataset_id": "TCGA-LIHC"}}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g14_skip_no_dataset() -> None:
    gate = G14DatasetPatientMatchGate()
    r = gate.check({})
    assert r.status == GateStatus.SKIP
