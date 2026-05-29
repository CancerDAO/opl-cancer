"""G40 drug_comorbidity_safety — reasoning-quality layer (ADR-0026 P1/P2).

Replays cross-model Finding 5 (MAJOR): a bevacizumab-containing backbone was
recommended for a patient with a cardiac workup on file, and the report never
reconciled the vasculotoxic agent with the cardiac history. The blocking case
asserts G40 BLOCKS that; the clean case asserts it PASSES when the loop is
closed; the SKIP case asserts it does NOT fire when the field it needs is absent
(it must NOT be dead-code-that-only-skips).

Imports the gate module DIRECTLY so the test runs before the orchestrator
registers the gate.

Run:
  PYTHONPATH=/Users/baozhiwei/cancerdao-review/repos/opl-cancer/src \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python3 -m pytest tests/test_validators/test_g40_reasoning.py -q
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.validators.gates.g40_drug_comorbidity_safety import (
    G40DrugComorbiditySafetyGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _write_profile(pdir: Path, comorbidities: list) -> None:
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "profile.json").write_text(
        json.dumps({
            "patient_code": "anon_test_001",
            "diagnosis": {"primary_site": "rectum", "kras_status": "G12C", "mss_status": "MSS"},
            "comorbidities": comorbidities,
        }),
        encoding="utf-8",
    )


# ── BLOCKING case: replay Finding 5 ─────────────────────────────────────────

def test_g40_blocks_bevacizumab_for_cardiac_patient(tmp_path: Path) -> None:
    """Finding 5: bevacizumab recommended, cardiac history never reconciled."""
    pdir = tmp_path / "patient"
    # the EXACT incident shape: a cardiac workup / cardiac history on file
    _write_profile(pdir, ["cardiac workup abnormal", "stage-1 hypertension"])
    claim = {
        "claim_id": "c_001",
        "claim_text": "Recommend FOLFOX + bevacizumab as the next-line backbone.",
        "drugs_mentioned": ["bevacizumab", "oxaliplatin"],
        # comorbidity_safety NOT present — the collision was never reconciled
        "patient_dir": str(pdir),
    }
    res = G40DrugComorbiditySafetyGate().check(claim)
    assert res.status is GateStatus.FAIL and res.block, res.message
    classes = {v["contraindication_class"] for v in res.evidence["violations"]}
    # both the cardiac and the hypertension collision should fire
    assert any("cardiac" in c for c in classes), classes
    assert any(
        "cardiac" in v["colliding_comorbidities"][0].lower()
        or "cardiac workup abnormal" in v["colliding_comorbidities"]
        for v in res.evidence["violations"]
    )


def test_g40_blocks_when_addressed_but_wrong_comorbidity_considered(tmp_path: Path) -> None:
    """Loop only half-closed: addressed==true but the cardiac comorbidity is not
    in comorbidities_considered (it considered a different one)."""
    pdir = tmp_path / "patient2"
    _write_profile(pdir, ["chronic heart failure"])
    claim = {
        "claim_id": "c_002",
        "claim_text": "Recommend bevacizumab maintenance.",
        "drugs_mentioned": ["bevacizumab"],
        "comorbidity_safety": {
            "addressed": True,
            "comorbidities_considered": ["diabetes"],  # NOT the cardiac one
            "note": "weighed diabetes",
        },
        "patient_dir": str(pdir),
    }
    res = G40DrugComorbiditySafetyGate().check(claim)
    assert res.status is GateStatus.FAIL and res.block, res.message


# ── CLEAN passing case: the loop is closed ──────────────────────────────────

def test_g40_passes_when_loop_closed(tmp_path: Path) -> None:
    pdir = tmp_path / "patient3"
    _write_profile(pdir, ["chronic heart failure", "stage-1 hypertension"])
    claim = {
        "claim_id": "c_003",
        "claim_text": "Considered bevacizumab; reconciled against cardiac/hypertension history.",
        "drugs_mentioned": ["bevacizumab"],
        "comorbidity_safety": {
            "addressed": True,
            "comorbidities_considered": ["chronic heart failure", "stage-1 hypertension"],
            "note": (
                "Bevacizumab's CHF/arterial-thromboembolism and hypertension risk weighed "
                "against the patient's cardiac history; cardiology co-management proposed."
            ),
        },
        "patient_dir": str(pdir),
    }
    res = G40DrugComorbiditySafetyGate().check(claim)
    assert res.status is GateStatus.PASS, res.message
    assert res.evidence["collisions_checked"] >= 1


def test_g40_passes_no_collision(tmp_path: Path) -> None:
    """A drug whose labelled classes don't collide with this patient passes."""
    pdir = tmp_path / "patient4"
    _write_profile(pdir, ["T2DM"])  # no cardiac/HTN/renal/hepatic collision
    claim = {
        "claim_id": "c_004",
        "claim_text": "Recommend bevacizumab.",
        "drugs_mentioned": ["bevacizumab"],
        "patient_dir": str(pdir),
    }
    res = G40DrugComorbiditySafetyGate().check(claim)
    assert res.status is GateStatus.PASS, res.message
    assert res.evidence["collisions_checked"] == 0


# ── SKIP cases: missing field ⇒ cannot judge (NOT a violation) ──────────────

def test_g40_skips_no_drugs(tmp_path: Path) -> None:
    pdir = tmp_path / "patient5"
    _write_profile(pdir, ["chronic heart failure"])
    res = G40DrugComorbiditySafetyGate().check({
        "claim_id": "c_005",
        "claim_text": "No drug invoked here.",
        "patient_dir": str(pdir),
    })
    assert res.status is GateStatus.SKIP and not res.block, res.message


def test_g40_skips_no_profile() -> None:
    res = G40DrugComorbiditySafetyGate().check({
        "claim_id": "c_006",
        "claim_text": "Recommend bevacizumab.",
        "drugs_mentioned": ["bevacizumab"],
        # no patient_dir / profile / comorbidities ⇒ cannot judge
    })
    assert res.status is GateStatus.SKIP and not res.block, res.message


def test_g40_skips_drug_not_in_reference(tmp_path: Path) -> None:
    pdir = tmp_path / "patient7"
    _write_profile(pdir, ["chronic heart failure"])
    res = G40DrugComorbiditySafetyGate().check({
        "claim_id": "c_007",
        "claim_text": "Recommend some-investigational-agent-xyz.",
        "drugs_mentioned": ["some-investigational-agent-xyz"],
        "patient_dir": str(pdir),
    })
    assert res.status is GateStatus.SKIP and not res.block, res.message


# ── CJK comorbidity collision (the records are often Chinese) ────────────────

def test_g40_blocks_cjk_cardiac_comorbidity(tmp_path: Path) -> None:
    pdir = tmp_path / "patient8"
    _write_profile(pdir, ["心脏功能检查异常", "乙肝病毒携带"])
    claim = {
        "claim_id": "c_008",
        "claim_text": "推荐含贝伐珠单抗方案。",
        "drugs_mentioned": ["bevacizumab"],
        "patient_dir": str(pdir),
    }
    res = G40DrugComorbiditySafetyGate().check(claim)
    assert res.status is GateStatus.FAIL and res.block, res.message
    assert any(
        "心脏功能检查异常" in v["colliding_comorbidities"]
        for v in res.evidence["violations"]
    )


def test_g40_uses_explicit_comorbidities_override(tmp_path: Path) -> None:
    """claim.comorbidities (no patient_dir) is honoured."""
    res = G40DrugComorbiditySafetyGate().check({
        "claim_id": "c_009",
        "claim_text": "Recommend regorafenib.",
        "drugs_mentioned": ["regorafenib"],
        "comorbidities": ["liver cirrhosis (Child-Pugh A)"],
        # regorafenib carries a BOXED hepatotoxicity warning → collision
    })
    assert res.status is GateStatus.FAIL and res.block, res.message
