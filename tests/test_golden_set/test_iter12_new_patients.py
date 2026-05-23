"""Iter 12 — golden-set sanity tests for 4 new synthetic patients + edge cases.

Verifies:
- profile.json / readiness.json / case_text.md / timeline.md all present
- ≥2 bucket files (NGS + pathology at minimum) per memory:feedback_multi_case_validation
- Pediatric safeguards present where indicated
- No real-PHI patterns leak
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GS_PATIENTS = REPO_ROOT / "validators" / "golden_set" / "synthetic_patients"

NEW_PATIENTS: tuple[str, ...] = (
    "anon_pancreatic_001",
    "anon_gbm_001",
    "anon_ped_all_001",
    "anon_myeloma_001",
)

ALL_PATIENTS: tuple[str, ...] = (
    "anon_hcc_001",
    "anon_nsclc_001",
    "anon_crc_001",
    "anon_brca_001",
    *NEW_PATIENTS,
)


@pytest.mark.parametrize("code", NEW_PATIENTS)
def test_patient_dir_exists(code: str) -> None:
    assert (GS_PATIENTS / code).is_dir(), f"missing patient dir {code}"


@pytest.mark.parametrize("code", NEW_PATIENTS)
def test_canonical_files_present(code: str) -> None:
    root = GS_PATIENTS / code
    for fname in ("profile.json", "readiness.json", "case_text.md", "timeline.md"):
        assert (root / fname).exists(), f"{code}: missing {fname}"


@pytest.mark.parametrize("code", NEW_PATIENTS)
def test_profile_schema_minimal(code: str) -> None:
    p = json.loads((GS_PATIENTS / code / "profile.json").read_text(encoding="utf-8"))
    assert p["patient_code"] == code
    assert "demographics" in p and "diagnosis" in p
    assert "treatment_history" in p and isinstance(p["treatment_history"], list)
    assert "preferences" in p
    assert p["preferences"]["language"] == "zh-CN"


@pytest.mark.parametrize("code", NEW_PATIENTS)
def test_readiness_ready_for_wave1(code: str) -> None:
    r = json.loads((GS_PATIENTS / code / "readiness.json").read_text(encoding="utf-8"))
    assert r["ready_for_wave1"] is True
    assert 0.5 <= r["score"] <= 1.0


@pytest.mark.parametrize("code", NEW_PATIENTS)
def test_at_least_two_buckets_with_files(code: str) -> None:
    root = GS_PATIENTS / code
    buckets_with_files = [
        d for d in root.iterdir() if d.is_dir() and any(d.iterdir())
    ]
    assert len(buckets_with_files) >= 2, (
        f"{code}: needs ≥2 buckets with files; have "
        f"{[b.name for b in buckets_with_files]}"
    )


def test_pediatric_safeguards_present() -> None:
    """Edge case 1 — pediatric patient must declare guardian + assent."""
    p = json.loads(
        (GS_PATIENTS / "anon_ped_all_001" / "profile.json").read_text(encoding="utf-8")
    )
    assert p["guardian_consent"]["parents_confirmed"] is True
    assert p["guardian_consent"]["patient_assent_age_appropriate"] is True
    assert p["preferences"]["depth"] == "guardian-and-pediatric"


def test_high_risk_cytogenetics_declared() -> None:
    """Edge case 2 — high-risk myeloma must carry risk_category."""
    p = json.loads(
        (GS_PATIENTS / "anon_myeloma_001" / "profile.json").read_text(encoding="utf-8")
    )
    assert "high" in p["diagnosis"]["risk_category"].lower()
    assert "t(4;14)" in p["molecular"]["cytogenetics"]
    assert "del(17p)" in p["molecular"]["cytogenetics"]


def test_brca_germline_documented() -> None:
    """Edge case 3 — pancreatic patient with germline BRCA2 must declare it in comorbidities."""
    p = json.loads(
        (GS_PATIENTS / "anon_pancreatic_001" / "profile.json").read_text(encoding="utf-8")
    )
    assert any("BRCA2" in c for c in p["comorbidities"]), (
        "BRCA2 germline must be declared in comorbidities for HRD-aware planning"
    )


def test_no_real_name_patterns() -> None:
    """No 'John' / 'Wang' / 'Li' / real-looking names in narrative text.

    Tolerates absent case_text.md / timeline.md on older P6 patients (they may
    be slim profile-only fixtures); only enforces presence for new Iter 12 set.
    """
    forbidden_names = {"John", "Jane", "Smith", "王某某", "李某某", "张某某"}
    for code in ALL_PATIENTS:
        for fname in ("case_text.md", "timeline.md"):
            f = GS_PATIENTS / code / fname
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            for n in forbidden_names:
                assert n not in text, f"{code}/{fname} contains suspected real name {n!r}"


def test_synthetic_marker_present() -> None:
    """case_text.md must declare SYNTHETIC."""
    for code in NEW_PATIENTS:
        text = (GS_PATIENTS / code / "case_text.md").read_text(encoding="utf-8")
        assert "SYNTHETIC" in text, f"{code}/case_text.md missing SYNTHETIC marker"
