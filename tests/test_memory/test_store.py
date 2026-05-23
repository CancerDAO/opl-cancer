"""Test ProjectMemoryStore — SQLite-backed insight card storage."""
from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.fixture()
def store(tmp_path: Path) -> ProjectMemoryStore:
    return ProjectMemoryStore(db_path=tmp_path / "memory.sqlite")


def _make_card(
    card_id: str = "ins_test", layer: ClaimLayer = ClaimLayer.ESTABLISHED
) -> InsightCard:
    return InsightCard(
        id=card_id,
        version=1,
        claim="test claim",
        claim_layer=layer,
        evidence=[Evidence(type=EvidenceType.PMID, id="999", quote="q")],
        produced_by=ProducedBy(executor_task="t", model="m", prompt_version="v", run_id="r"),
        reviewed_by=ReviewedBy(reviewer_model="rm", verdict="pass"),
        audited_by=AuditedBy(auditor_run="a", permission_level=1),
        provenance_hash="sha256:" + "0" * 64,
        created_at="2026-05-23T00:00:00Z",
    )


def test_save_and_retrieve_card(store: ProjectMemoryStore) -> None:
    card = _make_card("ins_001")
    store.save_insight(card)
    retrieved = store.get_insight("ins_001", version=1)
    assert retrieved is not None
    assert retrieved.claim == "test claim"


def test_save_card_creates_new_version_not_overwrite(store: ProjectMemoryStore) -> None:
    v1 = _make_card("ins_002")
    store.save_insight(v1)
    v2 = _make_card("ins_002").model_copy(update={"version": 2, "claim": "v2 claim"})
    store.save_insight(v2)
    v1_loaded = store.get_insight("ins_002", version=1)
    v2_loaded = store.get_insight("ins_002", version=2)
    assert v1_loaded is not None and v1_loaded.claim == "test claim"
    assert v2_loaded is not None and v2_loaded.claim == "v2 claim"


def test_query_by_layer(store: ProjectMemoryStore) -> None:
    store.save_insight(_make_card("ins_e", ClaimLayer.ESTABLISHED))
    store.save_insight(_make_card("ins_x", ClaimLayer.EXPLORATORY))
    store.save_insight(_make_card("ins_s", ClaimLayer.SPECULATIVE))
    cards = store.query_by_layer(ClaimLayer.EXPLORATORY)
    assert len(cards) == 1
    assert cards[0].id == "ins_x"


def test_query_excludes_withdrawn(store: ProjectMemoryStore) -> None:
    card = _make_card("ins_w")
    store.save_insight(card)
    store.withdraw_insight(
        "ins_w", version=1, reason="retracted PMID", at="2026-05-24T00:00:00Z"
    )
    cards = store.query_by_layer(ClaimLayer.ESTABLISHED, include_withdrawn=False)
    assert "ins_w" not in {c.id for c in cards}


def test_indexes_exist(store: ProjectMemoryStore) -> None:
    """Spec §17.5 P1 optimization: composite index on (claim_layer, withdraw_status)."""
    with store._conn() as conn:
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='insights'"
        ).fetchall()
    names = {r[0] for r in idx}
    assert any("layer" in n for n in names), names


def test_acknowledge_insight_propagates_timestamp(store: ProjectMemoryStore) -> None:
    """Iter 9 #4 — patient_acknowledged_at propagation into InsightCard."""
    card = _make_card("ins_ack_1")
    store.save_insight(card)
    updated = store.acknowledge_insight(
        "ins_ack_1", version=1, acknowledged_at="2026-05-24T10:00:00Z"
    )
    assert updated.patient_acknowledged_at == "2026-05-24T10:00:00Z"
    reloaded = store.get_insight("ins_ack_1", version=1)
    assert reloaded is not None
    assert reloaded.patient_acknowledged_at == "2026-05-24T10:00:00Z"


def test_acknowledge_missing_insight_raises(store: ProjectMemoryStore) -> None:
    """Acknowledging a non-existent card raises KeyError (no silent no-op)."""
    with pytest.raises(KeyError):
        store.acknowledge_insight("nonexistent", version=1, acknowledged_at="t")


def test_acknowledge_preserves_other_fields(store: ProjectMemoryStore) -> None:
    """Acknowledge does not clobber existing claim/evidence/audit data."""
    card = _make_card("ins_ack_2")
    store.save_insight(card)
    store.acknowledge_insight(
        "ins_ack_2", version=1, acknowledged_at="2026-05-24T11:00:00Z"
    )
    reloaded = store.get_insight("ins_ack_2", version=1)
    assert reloaded is not None
    assert reloaded.claim == "test claim"
    assert reloaded.evidence[0].id == "999"
    assert reloaded.audited_by.permission_level == 1
