"""v2.7.0 ADR-0026 — delivery-integrity + anti-fabrication + completeness gates.

Each test replays the concrete failure mode from session 0d1017d4
(KRAS-G12C / MSS-CRC free-handed report) and asserts the gate BLOCKS it,
plus the positive (properly-grounded) case PASSES.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal
from opl_cancer.validators.gates import (
    G34DeliveryAttestationGate,
    G35ClinicalFactProvenanceGate,
    G36PMIDTopicRelevanceGate,
    G37ServiceCompletenessGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


# ─── G35 clinical-fact provenance (the fabricated-lab fix) ──────────────────

def test_g35_blocks_fabricated_lab_value(tmp_path: Path) -> None:
    pdir = tmp_path / "patient"
    pdir.mkdir()
    # the EXACT incident: a confidently-stated lab value with no source anchor
    (pdir / "case_text.md").write_text(
        "肌酐 88 (正常)，GGT 19，肝功能 Child-Pugh A。\n", encoding="utf-8"
    )
    res = G35ClinicalFactProvenanceGate().check({"patient_dir": str(pdir)})
    assert res.status is GateStatus.FAIL and res.block
    assert res.evidence["violations"]


def test_g35_passes_anchored_lab_value(tmp_path: Path) -> None:
    pdir = tmp_path / "patient"
    (pdir / "ocr").mkdir(parents=True)
    (pdir / "ocr" / "labs.txt").write_text("肌酐 88 umol/L\n", encoding="utf-8")
    (pdir / "case_text.md").write_text(
        "肌酐 88 [[src:ocr/labs.txt#L1]]\n", encoding="utf-8"
    )
    res = G35ClinicalFactProvenanceGate().check({"patient_dir": str(pdir)})
    assert res.status is GateStatus.PASS, res.message


def test_g35_blocks_anchor_to_nonexistent_file(tmp_path: Path) -> None:
    pdir = tmp_path / "patient"
    pdir.mkdir()
    (pdir / "case_text.md").write_text(
        "ECOG 1 [[src:ocr/does_not_exist.txt#L1]]\n", encoding="utf-8"
    )
    res = G35ClinicalFactProvenanceGate().check({"patient_dir": str(pdir)})
    assert res.status is GateStatus.FAIL and res.block


def test_g35_unknown_value_is_honest_and_passes(tmp_path: Path) -> None:
    pdir = tmp_path / "patient"
    pdir.mkdir()
    (pdir / "case_text.md").write_text(
        "NRAS: UNKNOWN（未检测）\nBRAF 状态未知\n", encoding="utf-8"
    )
    res = G35ClinicalFactProvenanceGate().check({"patient_dir": str(pdir)})
    assert res.status in (GateStatus.PASS, GateStatus.SKIP), res.message


# ─── G36 PMID topical relevance (the wrong-paper-PMID fix) ──────────────────

class _FakePubMed:
    """Stand-in for PubMedIntegrator with a fixed PMID→record table."""

    def __init__(self, table: dict[str, dict]) -> None:
        self.table = table

    async def cached_fetch(self, key: str) -> dict:
        pmid = key.split(":", 1)[1] if ":" in key else key
        from opl_cancer.integrators.base import IntegratorError
        if pmid not in self.table:
            raise IntegratorError(f"PMID {pmid} not found")
        return self.table[pmid]


@pytest.mark.asyncio
async def test_g36_blocks_real_but_wrong_paper() -> None:
    # PMID 32366523 in the incident actually points to a knee-osteoarthritis letter.
    fake = _FakePubMed({
        "32366523": {
            "pmid": "32366523",
            "title": "Energy balance and knee osteoarthritis progression",
            "abstract": "A study of cartilage and body-mass in knee OA patients.",
            "journal": "Ann Rheum Dis",
        }
    })
    gate = G36PMIDTopicRelevanceGate(fake)
    claim = {
        "claim_text": "ATM loss confers greater ATR-inhibitor sensitivity in prostate cancer",
        "entities": ["ATM", "ATR", "PARP", "prostate"],
        "evidence": [{"type": "pmid", "id": "32366523", "quote": "ATM loss..."}],
    }
    res = await gate.check_async(claim)
    assert res.status is GateStatus.FAIL and res.block
    assert res.evidence["off_topic"][0]["real_title"].startswith("Energy balance")


@pytest.mark.asyncio
async def test_g36_passes_on_topic_paper() -> None:
    fake = _FakePubMed({
        "32127357": {
            "pmid": "32127357",
            "title": "ATM Loss Confers Greater Sensitivity to ATR Inhibition Than PARP Inhibition in Prostate Cancer",
            "abstract": "ATM-deficient prostate cancer models are more sensitive to ATR inhibitors.",
            "journal": "Cancer Res",
        }
    })
    gate = G36PMIDTopicRelevanceGate(fake)
    claim = {
        "entities": ["ATM", "ATR", "prostate"],
        "evidence": [{"type": "pmid", "id": "32127357", "quote": "ATM loss..."}],
    }
    res = await gate.check_async(claim)
    assert res.status is GateStatus.PASS, res.message


@pytest.mark.asyncio
async def test_g36_fails_closed_on_unfetchable_pmid() -> None:
    fake = _FakePubMed({})  # nothing fetchable
    gate = G36PMIDTopicRelevanceGate(fake)
    res = await gate.check_async({
        "entities": ["KRAS"],
        "evidence": [{"type": "pmid", "id": "99999999"}],
    })
    assert res.status is GateStatus.FAIL and res.block  # unverifiable ⇒ blocked


# ─── G37 service completeness (the 20→4 collapse / under-delivery fix) ──────

def _write_plan(run_root: Path, experts: list[str], waves: list[int]) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    tasks = [{"id": f"t{i}", "expert": e, "task_package": "x"} for i, e in enumerate(experts)]
    plan = {
        "goal": "next line", "tasks": tasks,
        "waves": [{"wave_number": w, "task_ids": [t["id"] for t in tasks]} for w in waves],
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")


def _write_report(run_root: Path, task_id: str, expert: str) -> None:
    d = run_root / "tasks" / f"w1_{task_id}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.md").write_text(f"# Wave 1 — {expert} / pkg\n\ntask_id: {task_id}\n", encoding="utf-8")


def test_g37_blocks_under_delivery(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run1"
    _write_plan(rr, ["rosa", "bert", "vince", "rick", "iain"], [1])
    # only ONE of five planned experts produced a report (the incident's shape)
    _write_report(rr, "t0", "rosa")
    res = G37ServiceCompletenessGate().check({"run_root": str(rr)})
    assert res.status is GateStatus.FAIL and res.block
    assert set(res.evidence["missing_experts"]) == {"bert", "vince", "rick", "iain"}


def test_g37_blocks_non_roster_collapse(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run2"
    _write_plan(rr, ["rosa", "bert"], [1])
    _write_report(rr, "t0", "rosa")
    # a generic agent stamped as author instead of the named persona
    d = rr / "tasks" / "w1_t1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.md").write_text("# Wave 1 — general-purpose / pkg\n\ntask_id: t1\n", encoding="utf-8")
    res = G37ServiceCompletenessGate().check({"run_root": str(rr)})
    assert res.status is GateStatus.FAIL and res.block
    assert "general-purpose" in res.evidence["non_roster_authors"]


def test_g37_passes_complete_run(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run3"
    experts = ["rosa", "bert", "vince"]
    _write_plan(rr, experts, [1])
    for i, e in enumerate(experts):
        _write_report(rr, f"t{i}", e)
    res = G37ServiceCompletenessGate().check({"run_root": str(rr)})
    assert res.status is GateStatus.PASS, res.message


def test_g37_user_replan_waiver_allows_drop(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run4"
    _write_plan(rr, ["rosa", "bert", "ted"], [1])
    _write_report(rr, "t0", "rosa")
    _write_report(rr, "t1", "bert")
    # ted dropped — but the PATIENT confirmed the narrower scope
    (rr / "replan.json").write_text(
        json.dumps({"confirmed_by_user": True, "dropped_experts": ["ted"]}), encoding="utf-8"
    )
    res = G37ServiceCompletenessGate().check({"run_root": str(rr)})
    assert res.status is GateStatus.PASS, res.message


def test_g37_blocks_missing_warranted_wave(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run5"
    experts = ["rosa", "bert"]
    _write_plan(rr, experts, [1, 2, 3])  # plan declared waves 2 and 3
    for i, e in enumerate(experts):
        _write_report(rr, f"t{i}", e)
    # no wave2/wave3 artifacts written → service silently shrank
    res = G37ServiceCompletenessGate().check({"run_root": str(rr)})
    assert res.status is GateStatus.FAIL and res.block
    assert set(res.evidence["missing_waves"]) >= {2, 3}


# ─── G34 delivery attestation (the free-handing keystone fix) ───────────────

def test_g34_blocks_free_handed_brief(tmp_path: Path) -> None:
    # the incident: a brief written into a folder with NO run behind it.
    rr = tmp_path / "triggers" / "run1"
    delivery = rr / "delivery"
    delivery.mkdir(parents=True)
    (delivery / "patient_pi_brief.md").write_text(
        "# Brief\nRecommend adagrasib + cetuximab [PMID:36546659].\n", encoding="utf-8"
    )
    res = G34DeliveryAttestationGate().check({"run_root": str(rr), "out_dir": str(delivery)})
    assert res.status is GateStatus.FAIL and res.block
    # all three structural pillars missing
    assert any("run_manifest" in p for p in res.evidence["problems"])
    assert any("provenance.jsonl" in p for p in res.evidence["problems"])
    assert any("Henry audit" in p for p in res.evidence["problems"])


def test_g34_passes_real_run(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run2"
    delivery = rr / "delivery"
    delivery.mkdir(parents=True)
    # 1. manifest with token
    (rr / "run_manifest.json").write_text(
        json.dumps({"run_id": "run2", "run_token": "tok-abc-123"}), encoding="utf-8"
    )
    # 2. provenance journal with a recomputable-hash record
    claim_payload = {"claim_id": "c1", "text": "established finding", "evidence": [{"type": "pmid", "id": "36546659"}]}
    j = ProvenanceJournal(rr / "provenance.jsonl")
    j.append({"claim": claim_payload, "hash": hash_claim(claim_payload)})
    # 3. real Henry audit
    (delivery / "HENRY_AUDIT.json").write_text(
        json.dumps({"henry_real_audit": True, "claims_audited": 1, "status": "pass"}), encoding="utf-8"
    )
    # 4. brief whose PMID is in the journal
    (delivery / "patient_pi_brief.md").write_text(
        "Recommend adagrasib + cetuximab [PMID:36546659].\n", encoding="utf-8"
    )
    res = G34DeliveryAttestationGate().check({"run_root": str(rr), "out_dir": str(delivery)})
    assert res.status is GateStatus.PASS, res.message


def test_g34_blocks_orphan_pmid_in_brief(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "run3"
    delivery = rr / "delivery"
    delivery.mkdir(parents=True)
    (rr / "run_manifest.json").write_text(json.dumps({"run_token": "t"}), encoding="utf-8")
    payload = {"claim_id": "c1", "evidence": [{"type": "pmid", "id": "36546659"}]}
    ProvenanceJournal(rr / "provenance.jsonl").append({"claim": payload, "hash": hash_claim(payload)})
    (delivery / "HENRY_AUDIT.json").write_text(
        json.dumps({"henry_real_audit": True, "claims_audited": 1}), encoding="utf-8"
    )
    # brief cites a PMID that was never journalled (invented at render time)
    (delivery / "patient_pi_brief.md").write_text(
        "Also consider drug X [PMID:99999999].\n", encoding="utf-8"
    )
    res = G34DeliveryAttestationGate().check({"run_root": str(rr), "out_dir": str(delivery)})
    assert res.status is GateStatus.FAIL and res.block
    assert any("99999999" in p for p in res.evidence["problems"])
