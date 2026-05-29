"""v2.6.0 — delivery must tell the truth about its own audit + scaffold state.

Independent product review (2026-05-29) found the v2.5.1 B1 "fix" replaced a
hardcoded {status: pass, gates_run: 28} with a *slightly less* hardcoded
{status: pass, gates_run: 4, henry_real_audit: true} that STILL never runs
HenryAuditor.audit_claim() and STILL ships placeholder-scaffold briefs. This
violates the product's own ADR-0021 (truthful execution) + discipline rule #1
(no false completion).

Truthful contract (v2.6.0):
  * Default (scaffold) deliver renders the template scaffold, runs the
    (CJK-aware) fakery sniffer, and — finding placeholders — reports
    status="scaffold_pending_fill", brief_complete=False, henry_real_audit=False,
    with a placeholder_findings list. It does NOT claim a real audit or a pass.
  * finalize=True over briefs that STILL contain placeholders REFUSES
    (DeliveryFailure) — a scaffold can never be finalized.
  * finalize=True over placeholder-clean briefs runs a REAL Henry audit
    (audit_claim over drugs found against the catalogue) and only then emits
    henry_real_audit=True + a gates_run that reflects the real audit.

These are the failing-first tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.glue.delivery_runner import DeliveryFailure, DeliveryRunner


def _complete_corpus(run_root: Path) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    w1 = run_root / "tasks" / "w1_rosa_pathology"
    w1.mkdir(parents=True, exist_ok=True)
    (w1 / "report.md").write_text(
        "# Wave 1 — rosa\nPer Awad et al. (PMID:34750504), ORR 23.2% (n=142).\n",
        encoding="utf-8",
    )
    (run_root / "plan.json").write_text('{"goal": "g", "tasks": ["t1"]}', encoding="utf-8")
    (run_root / "wave2_hypotheses.json").write_text(
        '{"hypotheses": [{"id": "h1"}]}', encoding="utf-8"
    )
    (run_root / "wave3_data_evidence.json").write_text(
        '{"analysis_runs": [{"id": "a1"}]}', encoding="utf-8"
    )
    (run_root / "wave4_validation.json").write_text(
        '{"validations": [{"id": "v1"}]}', encoding="utf-8"
    )


def test_scaffold_deliver_does_not_claim_real_audit(tmp_path: Path) -> None:
    run_root = tmp_path / "p" / "triggers" / "r1"
    _complete_corpus(run_root)
    out_dir = run_root / "delivery"

    result = DeliveryRunner(out_dir=out_dir).run()

    # The default scaffold path must be HONEST about being incomplete.
    assert result["status"] == "scaffold_pending_fill", result
    assert result["brief_complete"] is False, result
    assert result["henry_real_audit"] is False, result

    audit = json.loads((out_dir / "HENRY_AUDIT.json").read_text(encoding="utf-8"))
    assert audit["henry_real_audit"] is False
    assert audit["status"] != "pass"
    # It must point at the placeholder language it detected (ADR-0021 Inv-3).
    assert audit.get("placeholder_findings"), audit


def test_finalize_refuses_scaffold_with_placeholders(tmp_path: Path) -> None:
    run_root = tmp_path / "p" / "triggers" / "r1"
    _complete_corpus(run_root)
    out_dir = run_root / "delivery"
    # First produce the scaffold.
    DeliveryRunner(out_dir=out_dir).run()
    # Finalizing a brief that still has placeholders must REFUSE.
    with pytest.raises(DeliveryFailure):
        DeliveryRunner(out_dir=out_dir, finalize=True).run()


def test_finalize_runs_real_audit_on_clean_filled_brief(tmp_path: Path) -> None:
    run_root = tmp_path / "p" / "triggers" / "r1"
    _complete_corpus(run_root)
    out_dir = run_root / "delivery"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Simulate the SKILL main thread having filled both briefs with REAL,
    # placeholder-free content that mentions a catalogued drug (pembrolizumab).
    real_plain = (
        "# 患者简报\n\n## Section 0 · 一句话答案\n\n"
        "您目前在使用 pembrolizumab,影像显示部分缓解。\n"
        "建议与主治医生讨论免疫相关不良反应的监测计划。\n"
        "## Section 4 · 问医生的 5 个问题\n1. 我的 irAE 风险有多大?\n"
    )
    real_pi = (
        "# PI / Clinician Delivery Brief\n\n## Henry Audit\n"
        "Patient on pembrolizumab; monitor for immune-related adverse events.\n"
        "Per PMID:34750504, ORR 23.2%.\n"
    )
    (out_dir / "patient_plain_brief.md").write_text(real_plain, encoding="utf-8")
    (out_dir / "patient_pi_brief.md").write_text(real_pi, encoding="utf-8")

    # The CLAIMS (what is a claim, its level, which drugs it names) are produced
    # by the LLM/expert layer — NOT parsed out of free text by the runner. The
    # runner's job is the *mechanical* catalogue audit over structured claims.
    # (memory:feedback_default_prompt_over_script — no hardcoded NER in Python.)
    claims = {
        "claims": [
            {
                "claim_id": "c1",
                "claim_text": "Continue pembrolizumab; monitor for irAE.",
                "level": 3,
                "drugs_mentioned": ["pembrolizumab"],
            }
        ]
    }
    (run_root / "claims.json").write_text(json.dumps(claims), encoding="utf-8")

    result = DeliveryRunner(out_dir=out_dir, finalize=True).run()

    assert result["status"] in ("ok", "pending_acks"), result
    assert result["henry_real_audit"] is True, result
    assert result["brief_complete"] is True, result

    audit = json.loads((out_dir / "HENRY_AUDIT.json").read_text(encoding="utf-8"))
    assert audit["henry_real_audit"] is True
    # A REAL audit actually ran audit_claim over the structured claim.
    assert audit.get("claims_audited", 0) >= 1, audit
    # pembrolizumab's serious risks must surface from the catalogue (L3).
    blob = json.dumps(audit, ensure_ascii=False).lower()
    assert "pembrolizumab" in blob, audit
