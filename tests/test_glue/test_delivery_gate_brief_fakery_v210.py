"""v2.10 P0.3b/P0.3c — the delivery gate runner inspects the RENDERED BRIEF.

The core finding the 9-agent review reproduced: the gates inspected the
LLM-authored claims.json side-files, NOT the patient-facing brief text. A
fabricated brief with no claims.json shipped ok=True. These tests assert:

  * P0.3b: the fakery sniffer now runs over the FINAL briefs (placeholder
    language in the delivered brief hard-blocks).
  * P0.3c: a brief with clinical/treatment content but NO gated claims.json
    BLOCKS with `brief_has_claims_but_no_gated_claims`.
  * Red-team regression: a run dir with a brief recommending a drug + dose +
    invented efficacy and NO claims.json asserts ok=False.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.delivery_gate_runner import run_delivery_gates


def _build_attested_run(run_root: Path, *, with_claims: bool, brief_body: str) -> Path:
    """A structurally-complete, attested run (G34/G37 pass) so the only variable
    under test is the brief content vs. claims.json relationship."""
    out_dir = run_root / "delivery"
    out_dir.mkdir(parents=True)
    # G34 pillars
    (run_root / "run_manifest.json").write_text(
        json.dumps({"run_id": "r1", "run_token": "oplrun-deadbeef",
                    "planned_experts": ["rosa", "bert", "vince"], "planned_waves": [1]}),
        encoding="utf-8",
    )
    from opl_cancer.provenance.hasher import hash_claim
    from opl_cancer.provenance.journal import ProvenanceJournal
    payload = {"claim_id": "c1", "text": "x", "evidence": [{"type": "pmid", "id": "36546659"}]}
    ProvenanceJournal(run_root / "provenance.jsonl").append(
        {"claim": payload, "hash": hash_claim(payload)}
    )
    (out_dir / "HENRY_AUDIT.json").write_text(
        json.dumps({"henry_real_audit": True, "claims_audited": 1, "status": "pass"}),
        encoding="utf-8",
    )
    # G37 roster
    for i, e in enumerate(["rosa", "bert", "vince"]):
        d = run_root / "tasks" / f"w1_t{i}"
        d.mkdir(parents=True)
        (d / "report.md").write_text(f"# Wave 1 — {e} / pkg\n\ntask_id: t{i}\n", encoding="utf-8")
    # the brief under test
    (out_dir / "patient_pi_brief.md").write_text(brief_body, encoding="utf-8")
    if with_claims:
        (run_root / "claims.json").write_text(json.dumps({"claims": [{
            "claim_id": "c1", "entities": ["KRAS", "colorectal"],
            "evidence": [{"type": "pmid", "id": "36546659", "quote": "KRAS in colorectal"}],
        }]}), encoding="utf-8")
    return run_root


# ─── P0.3c — the red-team attack (regression) ───────────────────────────────

def test_redteam_fabricated_brief_no_claims_blocks(tmp_path: Path) -> None:
    """RED-TEAM REGRESSION: a brief recommending a drug + dose + invented efficacy
    with NO claims.json must ship ok=False (it shipped ok=True pre-v2.10)."""
    run_root = tmp_path / "triggers" / "r1"
    _build_attested_run(
        run_root,
        with_claims=False,
        brief_body=(
            "# 研究简报\n"
            "建议使用 adagrasib 600 mg BID 联合 cetuximab。\n"
            "客观缓解率 (ORR) 约为 62%，中位无进展生存 8.5 个月。\n"
        ),
    )
    verdict = run_delivery_gates(run_root=run_root, pubmed=None, write_attestation=False)
    assert verdict["ok"] is False, f"fabricated no-claims brief must block; {verdict['blocked_by']}"
    assert "brief_has_claims_but_no_gated_claims" in verdict["blocked_by"]


def test_brief_with_pmid_prose_but_no_claims_blocks(tmp_path: Path) -> None:
    """A brief that cites a PMID in prose but has no gated claims.json blocks."""
    run_root = tmp_path / "triggers" / "r2"
    _build_attested_run(
        run_root,
        with_claims=False,
        brief_body="Consider sotorasib per the literature [PMID:34161704].\n",
    )
    verdict = run_delivery_gates(run_root=run_root, pubmed=None, write_attestation=False)
    assert verdict["ok"] is False
    assert "brief_has_claims_but_no_gated_claims" in verdict["blocked_by"]


def test_empty_narrative_brief_no_claims_does_not_falsely_block(tmp_path: Path) -> None:
    """A brief with NO clinical/treatment content + no claims must not block on P0.3c
    (avoid false positives on a purely narrative / hand-off brief)."""
    run_root = tmp_path / "triggers" / "r3"
    _build_attested_run(
        run_root,
        with_claims=False,
        brief_body=(
            "# 研究简报\n"
            "本简报汇总了你的研究方向。最终决策权在你的主诊医生。\n"
        ),
    )
    verdict = run_delivery_gates(run_root=run_root, pubmed=None, write_attestation=False)
    assert "brief_has_claims_but_no_gated_claims" not in verdict["blocked_by"]


# ─── P0.3b — fakery sniffer over the final brief ────────────────────────────

def test_placeholder_in_delivered_brief_hard_blocks(tmp_path: Path) -> None:
    """A delivered brief still containing placeholder language must hard-block."""
    run_root = tmp_path / "triggers" / "r4"
    _build_attested_run(
        run_root,
        with_claims=True,
        brief_body="ORR: <insert value> in this cohort. TODO: confirm dose.\n",
    )
    verdict = run_delivery_gates(run_root=run_root, pubmed=None, write_attestation=False)
    assert verdict["ok"] is False
    assert "fakery_sniffer_delivery" in verdict["blocked_by"]


def test_clean_gated_brief_passes_fakery(tmp_path: Path) -> None:
    """A clean, gated brief whose efficacy is anchored does NOT block on fakery."""
    run_root = tmp_path / "triggers" / "r5"
    _build_attested_run(
        run_root,
        with_claims=True,
        brief_body="ORR was 43% [PMID:36546659]. 主诊医生为最终决策人。\n",
    )
    # pubmed=None means citation gates can't run → citation_gates_not_run blocks,
    # but fakery_sniffer_delivery must NOT be among the blockers.
    verdict = run_delivery_gates(run_root=run_root, pubmed=None, write_attestation=False)
    assert "fakery_sniffer_delivery" not in verdict["blocked_by"]
    assert "brief_has_claims_but_no_gated_claims" not in verdict["blocked_by"]
