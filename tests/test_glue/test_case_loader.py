"""Test PatientCaseLoader — patient_root → dispatch context dict."""
import json
from pathlib import Path

import pytest

from opl_cancer.glue.case_loader import PatientCaseLoader


def _setup_patient(tmp_path: Path, code: str) -> Path:
    base = tmp_path / code
    base.mkdir()
    (base / "profile.json").write_text(json.dumps({
        "patient_code": code,
        "demographics": {"age": 56, "sex": "M"},
        "diagnosis": {"primary_site": "liver", "histology": "HCC", "stage_BCLC": "C"},
        "treatment_history": [{"line": 1, "regimen": "TACE", "best_response": "PR"}],
        "comorbidities": ["HBV chronic"],
        "preferences": {"depth": "technical", "language": "zh-CN"},
    }))
    (base / "readiness.json").write_text(json.dumps({"score": 0.8, "missing": []}))
    (base / "case_text.md").write_text("# Case summary text\nHCC stage C TACE-refractory.")
    bucket = base / "02_NGS报告"
    bucket.mkdir()
    (bucket / "ngs.txt").write_text("EGFR L858R mutation detected. VAF 0.45.")
    return base


def test_load_returns_dict_with_keys(tmp_path: Path) -> None:
    base = _setup_patient(tmp_path, "anon_001")
    loader = PatientCaseLoader(patient_root=base)
    ctx = loader.load()
    assert ctx["patient_code"] == "anon_001"
    assert "profile" in ctx
    assert ctx["profile"]["diagnosis"]["histology"] == "HCC"
    assert "case_text" in ctx
    assert "ngs_report" in ctx
    assert "L858R" in ctx["ngs_report"]


def test_load_missing_profile_raises(tmp_path: Path) -> None:
    base = tmp_path / "no_profile"
    base.mkdir()
    loader = PatientCaseLoader(patient_root=base)
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_load_with_no_buckets_returns_empty_strings(tmp_path: Path) -> None:
    base = tmp_path / "minimal"
    base.mkdir()
    (base / "profile.json").write_text(json.dumps({
        "patient_code": "minimal",
        "demographics": {},
        "diagnosis": {},
        "treatment_history": [],
        "preferences": {"depth": "lay", "language": "zh-CN"},
    }))
    loader = PatientCaseLoader(patient_root=base)
    ctx = loader.load()
    assert ctx["patient_code"] == "minimal"
    assert ctx["readiness"] == {}
    assert ctx["case_text"] == ""
    # All bucket keys present even when empty
    for key in (
        "current_status", "ngs_report", "pathology_report", "imaging_report",
        "labs", "treatment_history_doc", "medication_list", "symptoms",
        "patient_feedback", "other_documents", "diagnosis_certificate",
    ):
        assert ctx[key] == "", f"expected empty string for {key}"


def test_load_concatenates_multiple_files_in_bucket(tmp_path: Path) -> None:
    base = _setup_patient(tmp_path, "multi")
    bucket = base / "02_NGS报告"
    (bucket / "ngs2.md").write_text("Additional NGS notes: TP53 wild-type.")
    ctx = PatientCaseLoader(patient_root=base).load()
    assert "L858R" in ctx["ngs_report"]
    assert "TP53 wild-type" in ctx["ngs_report"]
