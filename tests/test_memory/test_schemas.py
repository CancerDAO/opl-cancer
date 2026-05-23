"""Test insight card schema (spec §5.2)."""
import pytest
from pydantic import BaseModel, ValidationError

from opl_cancer.memory.schemas import (
    ClaimLayer,
    Evidence,
    EvidenceType,
    InsightCard,
    ProducedBy,
    ReviewedBy,
    AuditedBy,
)


def test_insight_card_minimum_valid() -> None:
    card = InsightCard(
        id="ins_a3f2c1",
        version=1,
        claim="Hypothetical claim text.",
        claim_layer=ClaimLayer.EXPLORATORY,
        evidence=[Evidence(type=EvidenceType.PMID, id="12345678", quote="...")],
        produced_by=ProducedBy(
            executor_task="hypothesis_generation",
            model="claude-opus-4-7",
            prompt_version="hypothesis_generation@v0.1.0",
            run_id="run_test",
        ),
        reviewed_by=ReviewedBy(
            reviewer_model="minimax-m2-7",
            verdict="pass",
            challenges=[],
            review_prompts_used=["pmid_quote_verify@v0.1"],
        ),
        audited_by=AuditedBy(
            auditor_run="audit_test",
            permission_level=2,
            clearances=["treatment_safeguard"],
            risk_card_id=None,
        ),
        provenance_hash="sha256:" + "0" * 64,
        created_at="2026-05-23T14:28:50Z",
    )
    assert card.id == "ins_a3f2c1"
    assert card.claim_layer == ClaimLayer.EXPLORATORY
    assert card.withdraw_status is None


def test_claim_layer_must_be_three_tier() -> None:
    class _Probe(BaseModel):
        layer: ClaimLayer

    with pytest.raises(ValidationError):
        _Probe(layer="invalid")


def test_pmid_evidence_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        Evidence(type=EvidenceType.PMID, id="", quote="anything")


def test_permission_level_in_range_0_to_4() -> None:
    with pytest.raises(ValidationError):
        AuditedBy(
            auditor_run="x",
            permission_level=5,  # out of range
            clearances=[],
            risk_card_id=None,
        )


def test_insight_card_rejects_empty_evidence_list() -> None:
    """Safety eval S6: every claim must cite at least one evidence."""
    with pytest.raises(ValidationError):
        InsightCard(
            id="ins_e", version=1,
            claim="claim", claim_layer=ClaimLayer.ESTABLISHED,
            evidence=[],
            produced_by=ProducedBy(executor_task="t", model="m", prompt_version="v", run_id="r"),
            reviewed_by=ReviewedBy(reviewer_model="rm", verdict="pass"),
            audited_by=AuditedBy(auditor_run="a", permission_level=1),
            provenance_hash="sha256:" + "0" * 64,
            created_at="2026-05-23T00:00:00Z",
        )


def test_pmid_evidence_rejects_empty_quote() -> None:
    """Safety eval S6: PMID evidence must have non-empty quote."""
    with pytest.raises(ValidationError):
        Evidence(type=EvidenceType.PMID, id="12345678", quote="")
