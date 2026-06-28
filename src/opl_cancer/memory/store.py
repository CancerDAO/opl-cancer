"""SQLite-backed Project Memory. Spec §5.1 + §17.5 (index optimization).

A1 (research-team iteration, ADR-0027) adds the **research ledger**: ONE
append-only, typed-record table that makes learning COMPOUND across runs.
Per the audit, OPL previously terminated at delivery and reset to zero every
run because every cross-run mechanism was orphaned. The ledger is the spine
those mechanisms hang off: hypotheses (incl. ``status='falsified'``),
tournament rounds, forecasts (C2), outcomes (A2), and failure piles (C3) all
persist here as typed rows. Append-only = Darwin's rule made structural — the
fact AGAINST a hypothesis is preserved beside it, never overwritten, so a
returning patient's already-killed direction is never silently re-proposed.

Deliberately ONE table with a ``record_type`` discriminator, not five
separate stores (the adversarial critic's consolidation: building five
ledgers would just create five new orphans).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .schemas import ClaimLayer, Hypothesis, InsightCard, TournamentRound, WithdrawStatus

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

CREATE TABLE IF NOT EXISTS ledger (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    run_id TEXT,
    status TEXT,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger(record_type, run_id);
CREATE INDEX IF NOT EXISTS idx_ledger_record ON ledger(record_id);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_patient_memory_db(run_root: Path) -> Path:
    """Canonical patient research-ledger DB path for a given run.

    Layout: ``<patient>/triggers/<run_id>/`` is the run_root, and the ledger
    lives at ``<patient>/memory/project_memory.db``. Used by both the delivery
    persistence step and the G54 gate so they agree on where the ledger is.
    """
    run_root = Path(run_root)
    patient_dir = run_root.parent.parent if run_root.parent.name == "triggers" else run_root.parent
    return patient_dir / "memory" / "project_memory.db"


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

    # ------------------------------------------------------------------
    # Research ledger (A1, ADR-0027) — one append-only typed-record table.
    # ------------------------------------------------------------------
    def append_ledger(
        self,
        record_type: str,
        record_id: str,
        payload: dict[str, Any],
        run_id: str | None = None,
        status: str | None = None,
    ) -> int:
        """Append one typed record. Append-only: never updates/replaces a row,
        so history (incl. falsified hypotheses) is preserved. Returns the seq."""
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO ledger "
                "(record_type, record_id, run_id, status, created_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record_type,
                    record_id,
                    run_id,
                    status,
                    _now_iso(),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid or 0)

    def save_hypothesis(self, hypothesis: Hypothesis, run_id: str | None = None) -> int:
        return self.append_ledger(
            "hypothesis",
            hypothesis.id,
            hypothesis.model_dump(mode="json"),
            run_id=run_id,
            status=hypothesis.status,
        )

    def save_tournament_round(
        self, round_: TournamentRound, run_id: str | None = None
    ) -> int:
        return self.append_ledger(
            "tournament_round",
            round_.round_id,
            round_.model_dump(mode="json"),
            run_id=run_id,
        )

    def ledger_rows(
        self, record_type: str | None = None, run_id: str | None = None
    ) -> list[dict[str, Any]]:
        sql = "SELECT payload_json FROM ledger WHERE 1=1"
        params: list[object] = []
        if record_type is not None:
            sql += " AND record_type=?"
            params.append(record_type)
        if run_id is not None:
            sql += " AND run_id=?"
            params.append(run_id)
        sql += " ORDER BY seq"
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def query_hypotheses(
        self, run_id: str | None = None, status: str | None = None
    ) -> list[Hypothesis]:
        out: list[Hypothesis] = []
        for payload in self.ledger_rows(record_type="hypothesis", run_id=run_id):
            h = Hypothesis.model_validate(payload)
            if status is not None and h.status != status:
                continue
            out.append(h)
        return out

    def query_tournament_rounds(
        self, run_id: str | None = None
    ) -> list[TournamentRound]:
        return [
            TournamentRound.model_validate(p)
            for p in self.ledger_rows(record_type="tournament_round", run_id=run_id)
        ]

    def ledger_count(
        self, run_id: str | None = None, record_type: str | None = None
    ) -> int:
        sql = "SELECT COUNT(*) FROM ledger WHERE 1=1"
        params: list[object] = []
        if run_id is not None:
            sql += " AND run_id=?"
            params.append(run_id)
        if record_type is not None:
            sql += " AND record_type=?"
            params.append(record_type)
        with self._conn() as conn:
            return int(conn.execute(sql, tuple(params)).fetchone()[0])

    def has_ledger_rows(self, run_id: str) -> bool:
        return self.ledger_count(run_id=run_id) > 0

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
