"""SQLite-backed cross-trigger integrator cache. Spec §17.5 P2."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    family TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (family, key)
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
"""


class IntegratorCache:
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

    def put(self, *, family: str, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (family, key, value_json, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (family, key, json.dumps(value), time.time() + ttl_seconds),
            )

    def get(self, *, family: str, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value_json FROM cache WHERE family=? AND key=? AND expires_at>?",
                (family, key, now),
            ).fetchone()
        return json.loads(row[0]) if row else None
