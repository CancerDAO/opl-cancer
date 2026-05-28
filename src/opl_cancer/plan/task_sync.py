"""v2.3 P2-#22 — TaskCreate / TaskUpdate sync helper.

When ``OPL_TASKCREATE_INTEGRATION=1`` is set, the planner emits one
``TaskCreate`` per wave at plan time, and wave-runners emit
``TaskUpdate(status=completed)`` on wave completion. The integration
is OFF by default — we do NOT depend on the Claude Code TaskCreate
tool in production code paths; the integration is a developer-mode
convenience for plan/code parity tracking.

The helper writes shell-readable JSONL into
``runs/<run_id>/task_sync.jsonl``. A separate adapter (out of scope
for the core library) actually calls the Claude Code TaskCreate /
TaskUpdate primitives if available. Keeping the helper pure-Python
keeps the OPL release reproducible regardless of harness.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


__all__ = [
    "is_taskcreate_enabled",
    "log_task_create",
    "log_task_update",
    "TASKCREATE_ENV_FLAG",
]


TASKCREATE_ENV_FLAG = "OPL_TASKCREATE_INTEGRATION"


def is_taskcreate_enabled() -> bool:
    return os.environ.get(TASKCREATE_ENV_FLAG, "0").strip() in {"1", "true", "yes", "on"}


def _log_path(run_dir: Path) -> Path:
    return Path(run_dir) / "task_sync.jsonl"


def _append(run_dir: Path, record: dict[str, Any]) -> None:
    path = _log_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_task_create(
    *,
    run_dir: Path,
    wave: int,
    subject: str,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a TaskCreate record. Always writes to JSONL.

    If ``OPL_TASKCREATE_INTEGRATION`` is enabled, the adapter (out of
    scope for this module) reads the JSONL and calls the real Claude
    Code TaskCreate primitive. We do not call TaskCreate from here.
    """
    record = {
        "kind": "TaskCreate",
        "ts": datetime.now(timezone.utc).isoformat(),
        "wave": wave,
        "subject": subject,
        "description": description,
        "metadata": metadata or {},
        "enabled": is_taskcreate_enabled(),
    }
    _append(run_dir, record)
    return record


def log_task_update(
    *,
    run_dir: Path,
    wave: int,
    status: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a TaskUpdate record (typically status=completed)."""
    record = {
        "kind": "TaskUpdate",
        "ts": datetime.now(timezone.utc).isoformat(),
        "wave": wave,
        "status": status,
        "metadata": metadata or {},
        "enabled": is_taskcreate_enabled(),
    }
    _append(run_dir, record)
    return record


def emit_plan_tasks_for_waves(
    *, run_dir: Path, waves: list[int], plan_summary: str = ""
) -> list[dict[str, Any]]:
    """One TaskCreate per wave at plan emit time. Returns the records."""
    out: list[dict[str, Any]] = []
    for w in waves:
        rec = log_task_create(
            run_dir=run_dir,
            wave=w,
            subject=f"Wave {w} execution",
            description=plan_summary or f"OPL Wave {w} pipeline",
            metadata={"source": "plan_emit"},
        )
        out.append(rec)
    return out


def mark_wave_completed(*, run_dir: Path, wave: int) -> dict[str, Any]:
    """Called by wave runners on success. Marks the TaskUpdate(completed)."""
    return log_task_update(run_dir=run_dir, wave=wave, status="completed")
