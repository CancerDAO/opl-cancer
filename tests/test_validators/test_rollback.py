"""Test rollback / withdraw protocol — spec §11."""
from pathlib import Path

from opl_cancer.memory.schemas import (
    AuditedBy, ClaimLayer, Evidence, EvidenceType, InsightCard,
    ProducedBy, ReviewedBy,
)
from opl_cancer.memory.store import ProjectMemoryStore
from opl_cancer.validators.rollback import withdraw_with_cascade


def _make(card_id: str, supersedes: str | None = None) -> InsightCard:
    return InsightCard(
        id=card_id, version=1,
        claim="c", claim_layer=ClaimLayer.ESTABLISHED,
        evidence=[Evidence(type=EvidenceType.PMID, id="1", quote="q")],
        produced_by=ProducedBy(executor_task="t", model="m", prompt_version="v", run_id="r"),
        reviewed_by=ReviewedBy(reviewer_model="rm", verdict="pass"),
        audited_by=AuditedBy(auditor_run="a", permission_level=1),
        provenance_hash="sha256:" + "0"*64,
        created_at="2026-05-23T00:00:00Z",
        supersedes=supersedes,
    )


def test_withdraw_marks_card_withdrawn(tmp_path: Path) -> None:
    store = ProjectMemoryStore(db_path=tmp_path / "m.sqlite")
    store.save_insight(_make("ins_a"))
    withdraw_with_cascade(store, "ins_a", version=1, reason="retracted", at="2026-05-24T00:00:00Z")
    assert store.get_insight("ins_a", 1).withdraw_status is not None


def test_withdraw_cascades_to_dependents(tmp_path: Path) -> None:
    store = ProjectMemoryStore(db_path=tmp_path / "m.sqlite")
    store.save_insight(_make("ins_a"))
    store.save_insight(_make("ins_b", supersedes="ins_a"))
    affected = withdraw_with_cascade(store, "ins_a", version=1, reason="retracted", at="2026-05-24T00:00:00Z")
    assert "ins_b" in affected


def test_withdraw_appends_to_journal_when_provided(tmp_path: Path) -> None:
    """Safety eval S3 — withdrawal must be reproducible from append-only journal."""
    from opl_cancer.provenance.journal import ProvenanceJournal

    store = ProjectMemoryStore(db_path=tmp_path / "m.sqlite")
    store.save_insight(_make("ins_j"))

    journal = ProvenanceJournal(path=tmp_path / "provenance.jsonl")
    withdraw_with_cascade(
        store, "ins_j", version=1, reason="retracted",
        at="2026-05-24T00:00:00Z", journal=journal,
    )

    records = list(journal.iter_records())
    assert len(records) == 1
    assert records[0]["event"] == "withdraw"
    assert records[0]["insight_id"] == "ins_j"
