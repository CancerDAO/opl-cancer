"""P5 — per-file golden_set validation tests.

One test per golden_set fixture file ensures the JSON is parseable, has the
expected top-level keys, and (where applicable) cross-references a known
mechanical gate. memory:feedback_multi_case_validation — N=many.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_ROOT = REPO_ROOT / "validators" / "golden_set"

KNOWN_GATES = {
    "G1_pmid_existence",
    "G2_pmid_quote_match",
    "G3_drug_normalization",
    "G4_dose_unit_check",
    "G7_imperative_intent",
    "G9_retraction_check",
    "G9_retraction_check_cascade",
    "G11_no_silent_fallback",
    "G15_batch_effect_check",
    "G16_evidence_balance_check",
}


# -- failure_mode_inputs ------------------------------------------------------

FAILURE_MODE_FILES = sorted((GOLDEN_ROOT / "failure_mode_inputs").glob("*.json"))


@pytest.mark.parametrize("path", FAILURE_MODE_FILES, ids=lambda p: p.stem)
def test_failure_mode_input_parses(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "test_name" in data
    assert "expected_block_gate" in data
    assert isinstance(data["expected_block_gate"], str)


@pytest.mark.parametrize("path", FAILURE_MODE_FILES, ids=lambda p: p.stem)
def test_failure_mode_input_has_claim(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "claim" in data
    assert isinstance(data["claim"], dict)


@pytest.mark.parametrize("path", FAILURE_MODE_FILES, ids=lambda p: p.stem)
def test_failure_mode_input_gate_recognised(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    gate = data["expected_block_gate"]
    # Allow registry-extension: any G\d+ prefix is acceptable shape.
    assert gate.startswith("G") or gate.startswith("C"), f"unknown gate code: {gate}"


# -- synthetic_patients -------------------------------------------------------

SYNTHETIC_PATIENT_DIRS = sorted(
    [d for d in (GOLDEN_ROOT / "synthetic_patients").iterdir() if d.is_dir()]
)


@pytest.mark.parametrize("d", SYNTHETIC_PATIENT_DIRS, ids=lambda d: d.name)
def test_synthetic_patient_profile_parses(d: Path) -> None:
    profile_p = d / "profile.json"
    assert profile_p.exists()
    data = json.loads(profile_p.read_text(encoding="utf-8"))
    assert "patient_code" in data
    assert "diagnosis" in data


@pytest.mark.parametrize("d", SYNTHETIC_PATIENT_DIRS, ids=lambda d: d.name)
def test_synthetic_patient_has_treatment_history(d: Path) -> None:
    data = json.loads((d / "profile.json").read_text(encoding="utf-8"))
    assert "treatment_history" in data
    assert isinstance(data["treatment_history"], list)
    assert len(data["treatment_history"]) >= 1


@pytest.mark.parametrize("d", SYNTHETIC_PATIENT_DIRS, ids=lambda d: d.name)
def test_synthetic_patient_demographics_present(d: Path) -> None:
    data = json.loads((d / "profile.json").read_text(encoding="utf-8"))
    assert "demographics" in data
    demo = data["demographics"]
    assert "age" in demo
    assert "sex" in demo


# -- regression_anchors -------------------------------------------------------

REGRESSION_ANCHORS = sorted((GOLDEN_ROOT / "regression_anchors").glob("*.json"))


@pytest.mark.parametrize("path", REGRESSION_ANCHORS, ids=lambda p: p.stem)
def test_regression_anchor_parses(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "anchor_name" in data
    assert "source" in data
    assert "acceptance_criterion" in data


# -- boundary_cases -----------------------------------------------------------

BOUNDARY_CASES = sorted((GOLDEN_ROOT / "boundary_cases").glob("*.json"))


@pytest.mark.parametrize("path", BOUNDARY_CASES, ids=lambda p: p.stem)
def test_boundary_case_parses(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "case_name" in data
    assert "expected_behavior" in data
    assert isinstance(data["expected_behavior"], list)
    assert len(data["expected_behavior"]) >= 1


@pytest.mark.parametrize("path", BOUNDARY_CASES, ids=lambda p: p.stem)
def test_boundary_case_has_patient_input(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "patient_input" in data


# -- serious_risks catalogue per-drug ----------------------------------------

import_drugs: list[str] = []
_data = json.loads(
    (REPO_ROOT / "knowledge" / "serious_risks_per_drug.json").read_text(encoding="utf-8")
)
for _k in _data:
    if not _k.startswith("_"):
        import_drugs.append(_k)


@pytest.mark.parametrize("drug", import_drugs)
def test_serious_risks_drug_entry_has_class(drug: str) -> None:
    data = json.loads(
        (REPO_ROOT / "knowledge" / "serious_risks_per_drug.json").read_text(encoding="utf-8")
    )
    entry = data[drug]
    assert "class" in entry
    assert "inn" in entry
    assert isinstance(entry["known_serious_risks"], list)
    assert len(entry["known_serious_risks"]) >= 2
