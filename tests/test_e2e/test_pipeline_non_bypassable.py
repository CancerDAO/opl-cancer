"""v2.7.0 ADR-0026 — the pipeline is non-bypassable, end to end.

Replays session 0d1017d4 at the CLI level: a free-handed brief (no run behind it,
fabricated PMIDs) must be REFUSED by every delivery entry point, while a complete,
grounded run PASSES. Multi-case (KRAS-CRC + EGFR-NSCLC) per
memory:feedback_multi_case_validation — one fixture does not prove generalisation.

Fails on pre-v2.7.0 main (render/audit were `{"ok":true}` stubs); passes after.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from opl_cancer.glue.delivery_gate_runner import run_delivery_gates
from opl_cancer.integrators.base import IntegratorError
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal


def _cli(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "opl_cancer.cli", *args, "--json"],
        capture_output=True, text=True,
    )
    try:
        return proc.returncode, json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return proc.returncode, {"raw": proc.stdout, "err": proc.stderr}


# ─── NEGATIVE: free-handed brief refused by every delivery entry point ──────

@pytest.mark.parametrize("command", ["audit", "render", "attest"])
def test_free_handed_brief_is_refused(tmp_path: Path, command: str) -> None:
    """The exact incident: a brief written with no run behind it (fabricated
    PMIDs, no manifest/provenance/audit/plan) must be refused — exit ≠ 0."""
    patient = tmp_path / "patients" / "PT-FREEHAND"
    delivery = patient / "triggers" / "r1" / "delivery"
    delivery.mkdir(parents=True)
    (delivery / "patient_pi_brief.md").write_text(
        "Recommend adagrasib+cetuximab [PMID:36546659]. ATM→ATRi [PMID:32366523].\n",
        encoding="utf-8",
    )
    rc, payload = _cli([command, "--patient", str(patient), "--run-id", "r1"])
    assert rc != 0, f"{command} must refuse a free-handed brief; got rc={rc} {payload}"
    assert payload["ok"] is False
    # the structural pillars are all missing
    assert "G34_delivery_attestation" in payload["blocked_by"]
    assert "G37_service_completeness" in payload["blocked_by"]


def test_go_refuses_raw_unorganised_input(tmp_path: Path) -> None:
    """`go` must NOT OCR raw uploads or proceed without an organised patient dir."""
    patient = tmp_path / "patients" / "PT-RAW"
    patient.mkdir(parents=True)
    (patient / "scan1.pdf").write_bytes(b"%PDF-1.4 fake")  # loose raw file
    rc, payload = _cli(["go", "--patient", str(patient), "--goal", "下一步怎么办"])
    assert payload["ok"] is False
    assert payload["stage"] == "input_guard"


def test_go_surfaces_full_team_never_collapses(tmp_path: Path) -> None:
    """From one simple goal, `go` must surface the FULL planned team to dispatch
    (the founder's 'one prompt → full service' requirement)."""
    patient = tmp_path / "patients" / "PT-GO"
    patient.mkdir(parents=True)
    (patient / "profile.json").write_text('{"patient_id_hash":"x"}', encoding="utf-8")
    (patient / "case_text.md").write_text("诊断: mCRC KRAS G12C MSS\n", encoding="utf-8")
    (patient / "readiness.json").write_text('{"grade":"B"}', encoding="utf-8")
    run_root = patient / "triggers" / "run-go"
    run_root.mkdir(parents=True)
    experts = ["rosa", "bert", "vince", "rick", "iain", "frances"]
    plan = {
        "goal": "三线方案",
        "tasks": [{"id": f"t{i}", "expert": e, "task_package": "x"} for i, e in enumerate(experts)],
        "waves": [{"wave_number": 1, "task_ids": ["t0"]}],
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    rc, payload = _cli(["go", "--patient", str(patient), "--run-id", "run-go", "--goal", "下一步"])
    assert payload["stage"] == "waves"
    assert set(payload["planned_experts"]) == set(experts)  # nothing dropped


# ─── POSITIVE: a complete, grounded run PASSES (with two cancer types) ───────

class _FakePubMed:
    def __init__(self, table: dict[str, dict]) -> None:
        self.table = table

    async def cached_fetch(self, key: str) -> dict:
        pmid = key.split(":", 1)[1] if ":" in key else key
        if pmid not in self.table:
            raise IntegratorError(f"PMID {pmid} not found")
        return self.table[pmid]


def _build_complete_run(root: Path, *, experts: list[str], pmid: str, gene: str, cancer: str) -> Path:
    """Assemble a fully-grounded run_root the way a real pipeline would."""
    patient = root / "patient"
    run_root = patient / "triggers" / "r1"
    out_dir = run_root / "delivery"
    (patient / "ocr").mkdir(parents=True)
    (patient / "ocr" / "labs.txt").write_text("肌酐 88 umol/L\n", encoding="utf-8")
    (patient / "case_text.md").write_text(
        f"诊断: {cancer} {gene} 突变。肌酐 88 [[src:ocr/labs.txt#L1]]\n", encoding="utf-8"
    )
    run_root.mkdir(parents=True)
    # plan + manifest (full team)
    plan = {
        "goal": "next line",
        "tasks": [{"id": f"t{i}", "expert": e, "task_package": "x"} for i, e in enumerate(experts)],
        "waves": [{"wave_number": 1, "task_ids": ["t0"]}],
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (run_root / "run_manifest.json").write_text(
        json.dumps({"run_id": "r1", "run_token": "oplrun-deadbeef",
                    "planned_experts": experts, "planned_waves": [1]}), encoding="utf-8"
    )
    # one report per planned expert (no collapse)
    for i, e in enumerate(experts):
        d = run_root / "tasks" / f"w1_t{i}"
        d.mkdir(parents=True)
        (d / "report.md").write_text(f"# Wave 1 — {e} / pkg\n\ntask_id: t{i}\n", encoding="utf-8")
    (run_root / "wave2_hypotheses.json").write_text('{"hypotheses":[{"id":"h1"}]}', encoding="utf-8")
    # provenance journal with a recomputable-hash record carrying the PMID
    payload = {"claim_id": "c1", "text": f"{gene} finding",
               "evidence": [{"type": "pmid", "id": pmid}]}
    ProvenanceJournal(run_root / "provenance.jsonl").append(
        {"claim": payload, "hash": hash_claim(payload)}
    )
    # claims manifest (entities for G36 relevance)
    (run_root / "claims.json").write_text(json.dumps({"claims": [{
        "claim_id": "c1", "entities": [gene, cancer],
        "evidence": [{"type": "pmid", "id": pmid, "quote": f"{gene} in {cancer}"}],
    }]}), encoding="utf-8")
    # filled briefs + real Henry audit
    out_dir.mkdir(parents=True)
    (out_dir / "patient_pi_brief.md").write_text(
        f"{gene} therapy supported [PMID:{pmid}].\n", encoding="utf-8"
    )
    (out_dir / "HENRY_AUDIT.json").write_text(
        json.dumps({"henry_real_audit": True, "claims_audited": 1, "status": "pass"}),
        encoding="utf-8",
    )
    return run_root


@pytest.mark.parametrize(
    "gene,cancer,pmid,title",
    [
        ("KRAS", "colorectal", "36546659", "Adagrasib in KRAS G12C colorectal cancer"),
        ("EGFR", "lung", "37870968", "Osimertinib in EGFR-mutant non-small-cell lung cancer"),
    ],
)
def test_complete_grounded_run_passes(tmp_path: Path, gene, cancer, pmid, title) -> None:
    experts = ["rosa", "bert", "vince"]
    run_root = _build_complete_run(
        tmp_path, experts=experts, pmid=pmid, gene=gene, cancer=cancer
    )
    fake = _FakePubMed({pmid: {"pmid": pmid, "title": title,
                              "abstract": f"{gene} alterations in {cancer} cancer.",
                              "journal": "NEJM"}})
    verdict = run_delivery_gates(run_root=run_root, pubmed=fake)
    assert verdict["ok"], f"complete run should pass; blocked_by={verdict['blocked_by']}"


def test_wrong_paper_pmid_blocks_complete_run(tmp_path: Path) -> None:
    """Even a structurally complete run is refused if a PMID is the wrong paper."""
    experts = ["rosa", "bert", "vince"]
    run_root = _build_complete_run(
        tmp_path, experts=experts, pmid="32366523", gene="KRAS", cancer="colorectal"
    )
    # 32366523 actually points to a knee-osteoarthritis paper (the incident).
    fake = _FakePubMed({"32366523": {
        "pmid": "32366523", "title": "Energy balance and knee osteoarthritis",
        "abstract": "Cartilage and body mass in knee OA.", "journal": "Ann Rheum Dis",
    }})
    verdict = run_delivery_gates(run_root=run_root, pubmed=fake)
    assert not verdict["ok"]
    assert "G36_pmid_topic_relevance" in verdict["blocked_by"]
