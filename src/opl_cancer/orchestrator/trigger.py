"""Trigger event loop — file drop / patient query / cron / lit signal. Spec §13."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field


class TriggerSource(str, Enum):
    PATIENT_QUERY = "patient_query"
    FILE_DROP = "file_drop"
    SCHEDULED = "scheduled"
    LITERATURE_SIGNAL = "literature_signal"
    INTEGRATOR_ALERT = "integrator_alert"


class TriggerEvent(BaseModel):
    source: TriggerSource
    data: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def scan_inbox(inbox_dir: Path) -> Iterator[TriggerEvent]:
    """Yield one TriggerEvent per file in inbox_dir. P0 only handles FILE_DROP."""
    if not inbox_dir.exists():
        return
    for p in sorted(inbox_dir.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            yield TriggerEvent(
                source=TriggerSource.FILE_DROP,
                data={"filename": p.name, "path": str(p)},
            )
