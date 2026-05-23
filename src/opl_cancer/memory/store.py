"""SQLite-backed Project Memory. Spec §5.1 + §17.5 (index optimization)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .schemas import ClaimLayer, InsightCard, WithdrawStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS insights (
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    claim_layer TEXT NOT NULL,
    withdraw_status TEXT,
    created_at TEXT NOT NULL,
    card_json TEXT NOT NULL,
    PRIMARY KEY (id, version)
);

CREATE INDEX IF NOT EXISTS idx_insights_layer ON insights(claim_layer, withdraw_status);
CREATE INDEX IF NOT EXISTS idx_insights_created ON insights(created_at);
"""


class ProjectMemoryStore:
    """Per-patient memory store. Each patient gets one SQLite DB."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_insight(self, card: InsightCard) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO insights "
                "(id, version, claim_layer, withdraw_status, created_at, card_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    card.id,
                    card.version,
                    card.claim_layer.value,
                    card.withdraw_status.model_dump_json() if card.withdraw_status else None,
                    card.created_at,
                    card.model_dump_json(),
                ),
            )

    def get_insight(self, card_id: str, version: int) -> InsightCard | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT card_json FROM insights WHERE id=? AND version=?",
                (card_id, version),
            ).fetchone()
        return InsightCard.model_validate_json(row[0]) if row else None

    def query_by_layer(
        self, layer: ClaimLayer, include_withdrawn: bool = False
    ) -> list[InsightCard]:
        sql = "SELECT card_json FROM insights WHERE claim_layer=?"
        params: tuple[object, ...] = (layer.value,)
        if not include_withdrawn:
            sql += " AND withdraw_status IS NULL"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [InsightCard.model_validate_json(r[0]) for r in rows]

    def withdraw_insight(
        self, card_id: str, version: int, reason: str, at: str, evidence: str = ""
    ) -> None:
        card = self.get_insight(card_id, version)
        if card is None:
            raise KeyError(f"insight {card_id}@v{version} not found")
        card = card.model_copy(
            update={
                "withdraw_status": WithdrawStatus(
                    reason=reason, withdrawn_at=at, evidence=evidence
                )
            }
        )
        self.save_insight(card)

    def acknowledge_insight(
        self, card_id: str, version: int, acknowledged_at: str
    ) -> InsightCard:
        """Mark an InsightCard as patient-acknowledged.

        Iter 9 #4 — propagation path for Henry L4 ack → memory store.
        Returns the updated card. Raises KeyError if not found.
        """
        card = self.get_insight(card_id, version)
        if card is None:
            raise KeyError(f"insight {card_id}@v{version} not found")
        card = card.model_copy(
            update={"patient_acknowledged_at": acknowledged_at}
        )
        self.save_insight(card)
        return card
