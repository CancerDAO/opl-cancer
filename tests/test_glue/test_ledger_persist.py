"""A1 — persist a finished run into the research ledger (the wiring).

This is the production caller that makes the compounding spine real: at
deliver/attest the run's hypotheses, tournament rounds, and delivered claims
are written to the patient ledger so run N+1 starts warm. Faithful, never
fabricating: a claim that already carries full InsightCard provenance is saved
as an InsightCard; anything lighter is preserved verbatim as a generic
``delivered_claim`` ledger row (no invented provenance).
"""
from __future__ import annotations

import json

from opl_cancer.glue.ledger_persist import persist_run_to_ledger
from opl_cancer.memory.schemas import (
    AuditedBy,
    ClaimLayer,
    Evidence,
    EvidenceType,
    InsightCard,
    ProducedBy,
    ReviewedBy,
)
from opl_cancer.memory.store import ProjectMemoryStore


def _valid_insight_card() -> InsightCard:
    return InsightCard(
        id="claim-1",
        version=1,
        claim="Sotorasib+panitumumab is a guideline option in this setting.",
        claim_layer=ClaimLayer.ESTABLISHED,
        evidence=[Evidence(type=EvidenceType.PMID, id="37870968", quote="ORR 26%")],
        produced_by=ProducedBy(
            executor_task="treatment_line", model="opus", prompt_version="v1", run_id="run-001"
        ),
        reviewed_by=ReviewedBy(reviewer_model="minimax", verdict="pass"),
        audited_by=AuditedBy(auditor_run="henry-1", permission_level=2),
        provenance_hash="sha256:" + "a" * 64,
        created_at="2026-06-28T00:00:00+00:00",
    )


def _run(tmp_path):
    run_root = tmp_path / "triggers" / "run-001"
    run_root.mkdir(parents=True)
    (run_root / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [
            {"id": "H1", "text": "MTAP-loss → PRMT5 synthetic lethality",
             "status": "active", "generation_strategy": "undrugged_target_design"},
            {"id": "H2", "text": "KRAS G12C + anti-EGFR", "status": "falsified"},
        ]}),
        encoding="utf-8",
    )
    (run_root / "claims.json").write_text(
        json.dumps({"claims": [
            _valid_insight_card().model_dump(mode="json"),
            {"claim_id": "c2", "claim_text": "lighter claim, no provenance"},
        ]}),
        encoding="utf-8",
    )
    return run_root


def test_persist_writes_hypotheses_and_claims(tmp_path):
    run_root = _run(tmp_path)
    db = tmp_path / "memory" / "project_memory.db"

    counts = persist_run_to_ledger(run_root, memory_db=db)

    assert counts["hypotheses"] == 2
    assert counts["insights"] == 1          # the valid InsightCard
    assert counts["delivered_claims"] == 1  # the lighter claim, faithfully kept

    store = ProjectMemoryStore(db)
    assert store.ledger_count(run_id="run-001", record_type="hypothesis") == 2
    # the falsified direction is preserved for the next run (Darwin log)
    assert any(h.id == "H2" for h in store.query_hypotheses(status="falsified"))
    # the full-provenance claim landed in the insights store, not the ledger
    assert store.get_insight("claim-1", 1) is not None


def test_persist_is_idempotent_safe_when_no_artifacts(tmp_path):
    run_root = tmp_path / "triggers" / "run-empty"
    run_root.mkdir(parents=True)
    db = tmp_path / "memory" / "project_memory.db"
    counts = persist_run_to_ledger(run_root, memory_db=db)
    assert counts == {"hypotheses": 0, "tournament_rounds": 0, "insights": 0, "delivered_claims": 0}
