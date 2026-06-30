"""Append-only structured run events for long OPL sessions.

The progress dashboard is a user-facing heartbeat. This module is the machine
log that lets the host re-ground, resume, render dashboards, and expose MCP
tools without scraping prose. It is deliberately LLM-free: callers provide the
event type and payload, the harness stamps and hashes the event.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "opl.run_event.v1"
SEVERITIES = frozenset({"debug", "info", "warn", "error"})


def event_log_path(run_root: Path) -> Path:
    """Canonical JSONL event log path for one trigger run."""
    return Path(run_root) / "run_events.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_event(event: dict[str, Any]) -> str:
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_run_event(
    *,
    run_root: Path,
    event_type: str,
    phase: str | None = None,
    source: str = "opl-cancer",
    severity: str = "info",
    payload: dict[str, Any] | None = None,
    at: str | None = None,
) -> dict[str, Any]:
    """Create a canonical event record without writing it."""
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}; expected one of {sorted(SEVERITIES)}")

    event = {
        "schema": SCHEMA,
        "run_id": Path(run_root).name,
        "event_type": event_type.strip(),
        "phase": (phase or "").strip() or None,
        "severity": severity,
        "source": source,
        "at": at or _now_iso(),
        "payload": dict(payload or {}),
    }
    event_hash = _hash_event(event)
    event["event_hash"] = event_hash
    event["event_id"] = event_hash.split(":", 1)[1][:16]
    return event


def append_run_event(
    run_root: Path,
    event_type: str,
    *,
    phase: str | None = None,
    source: str = "opl-cancer",
    severity: str = "info",
    payload: dict[str, Any] | None = None,
    at: str | None = None,
) -> dict[str, Any]:
    """Append one event to ``run_events.jsonl`` and return the persisted record."""
    run_root = Path(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    event = build_run_event(
        run_root=run_root,
        event_type=event_type,
        phase=phase,
        source=source,
        severity=severity,
        payload=payload,
        at=at,
    )
    with event_log_path(run_root).open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        f.write("\n")
    return event


def iter_run_events(
    run_root: Path,
    *,
    event_type: str | None = None,
    phase: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield valid run events, optionally filtered by type and phase."""
    path = event_log_path(run_root)
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type and event.get("event_type") != event_type:
                continue
            if phase and event.get("phase") != phase:
                continue
            yield event


def summarize_run_events(run_root: Path) -> dict[str, Any]:
    """Return a compact summary for ``observe`` and dashboards."""
    path = event_log_path(run_root)
    events = list(iter_run_events(run_root))
    by_type: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    for event in events:
        et = str(event.get("event_type") or "unknown")
        by_type[et] = by_type.get(et, 0) + 1
        phase = event.get("phase")
        if phase:
            ph = str(phase)
            by_phase[ph] = by_phase.get(ph, 0) + 1
    last = events[-1] if events else None
    return {
        "available": path.is_file(),
        "path": str(path),
        "count": len(events),
        "by_type": by_type,
        "by_phase": by_phase,
        "last_event": {
            "event_id": last.get("event_id"),
            "event_type": last.get("event_type"),
            "phase": last.get("phase"),
            "severity": last.get("severity"),
            "at": last.get("at"),
        } if last else None,
    }
