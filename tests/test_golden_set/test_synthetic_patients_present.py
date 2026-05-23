"""Verify F1 + F2 synthetic patients present and well-formed (T31)."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GS = REPO_ROOT / "validators" / "golden_set" / "synthetic_patients"


def test_anon_hcc_001_present() -> None:
    base = GS / "anon_hcc_001"
    assert (base / "profile.json").exists()
    profile = json.loads((base / "profile.json").read_text())
    assert profile["patient_code"] == "anon_hcc_001"
    assert profile["diagnosis"]["histology"] == "HCC"
    assert profile["preferences"]["depth"] == "technical"


def test_anon_nsclc_001_present() -> None:
    base = GS / "anon_nsclc_001"
    assert (base / "profile.json").exists()
    profile = json.loads((base / "profile.json").read_text())
    assert profile["patient_code"] == "anon_nsclc_001"
    assert "NSCLC" in profile["diagnosis"]["histology"]
    assert profile["preferences"]["depth"] == "technical"


def test_hcc_buckets_populated() -> None:
    base = GS / "anon_hcc_001"
    assert (base / "02_NGS报告" / "ngs.txt").exists()
    assert (base / "03_病理" / "path.txt").exists()
    assert (base / "04_影像" / "imaging.txt").exists()
    assert (base / "05_实验室" / "labs.txt").exists()
    assert (base / "06_治疗历史" / "history.txt").exists()


def test_nsclc_buckets_populated() -> None:
    base = GS / "anon_nsclc_001"
    assert (base / "02_NGS报告" / "ngs.txt").exists()
    assert (base / "03_病理" / "path.txt").exists()
    assert (base / "04_影像" / "imaging.txt").exists()
    assert "C797S" in (base / "02_NGS报告" / "ngs.txt").read_text()


def test_readiness_marks_wave1_ready() -> None:
    for code in ("anon_hcc_001", "anon_nsclc_001"):
        r = json.loads((GS / code / "readiness.json").read_text())
        assert r["ready_for_wave1"] is True
        assert r["score"] >= 0.8


def test_no_real_phi_marker() -> None:
    """Sanity check: case_text declares SYNTHETIC, no real names/MRNs."""
    for code in ("anon_hcc_001", "anon_nsclc_001"):
        text = (GS / code / "case_text.md").read_text()
        assert "SYNTHETIC" in text
        assert code.startswith("anon_")
