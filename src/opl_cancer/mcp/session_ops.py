"""Deterministic session operations behind the optional OPL MCP server.

These functions are intentionally thin and LLM-free. They expose the same
machine surfaces as the CLI so a host agent can call tools directly instead of
parsing stdout. Clinical claims are still governed by provenance and gates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opl_cancer.glue.run_events import (
    append_run_event,
    iter_run_events,
    load_run_checkpoint,
    summarize_run_events,
    write_run_checkpoint,
)


def _run_root(patient_dir: str | Path, run_id: str) -> Path:
    return Path(patient_dir) / "triggers" / run_id


def observe(patient_dir: str | Path, run_id: str) -> dict[str, Any]:
    """Return the same read-only run projection as ``opl-cancer observe --json``."""
    from opl_cancer.cli import _observe_projection

    return _observe_projection(Path(patient_dir), run_id)


def validate(patient_dir: str | Path, run_id: str) -> dict[str, Any]:
    """Return the same invariant summary as ``opl-cancer validate --json``."""
    from opl_cancer.cli import _validate_run_state

    problems = _validate_run_state(Path(patient_dir), run_id)
    errors = [p for p in problems if p["severity"] == "error"]
    return {
        "ok": not errors,
        "run_id": run_id,
        "errors": len(errors),
        "warnings": len(problems) - len(errors),
        "problems": problems,
    }


def recovery_plan(patient_dir: str | Path, run_id: str) -> dict[str, Any]:
    """Build a deterministic run recovery plan."""
    from opl_cancer.cli import _observe_projection, _validate_run_state
    from opl_cancer.glue.recovery import build_recovery_plan

    pdir = Path(patient_dir)
    return build_recovery_plan(
        pdir,
        run_id,
        projection=_observe_projection(pdir, run_id),
        validation_problems=_validate_run_state(pdir, run_id),
    )


def events_list(
    patient_dir: str | Path,
    run_id: str,
    *,
    event_type: str | None = None,
    phase: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List structured run events and a compact summary."""
    run_root = _run_root(patient_dir, run_id)
    records = list(iter_run_events(run_root, event_type=event_type, phase=phase))
    if limit >= 0:
        records = records[-limit:]
    return {
        "ok": True,
        "run_id": run_id,
        "summary": summarize_run_events(run_root),
        "events": records,
    }


def events_append(
    patient_dir: str | Path,
    run_id: str,
    event_type: str,
    *,
    phase: str | None = None,
    severity: str = "info",
    source: str = "opl_cancer.mcp.session_ops",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one structured event."""
    event = append_run_event(
        _run_root(patient_dir, run_id),
        event_type,
        phase=phase,
        severity=severity,
        source=source,
        payload=payload,
    )
    return {"ok": True, "event": event}


def checkpoint_read(patient_dir: str | Path, run_id: str) -> dict[str, Any]:
    """Read the latest resumable checkpoint."""
    checkpoint = load_run_checkpoint(_run_root(patient_dir, run_id))
    return {"ok": checkpoint is not None, "run_id": run_id, "checkpoint": checkpoint}


def checkpoint_write(
    patient_dir: str | Path,
    run_id: str,
    *,
    reason: str,
    phase: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a latest resumable checkpoint and its companion event."""
    if not reason.strip():
        raise ValueError("reason is required")
    checkpoint = write_run_checkpoint(
        _run_root(patient_dir, run_id),
        reason=reason,
        phase=phase,
        payload=payload,
    )
    return {"ok": True, "checkpoint": checkpoint}


def integrator_plugins() -> dict[str, Any]:
    """Return the discovered integrator entry-point inventory."""
    from opl_cancer.integrators._abc import ENTRY_POINT_GROUP, IntegratorRegistry

    rows = IntegratorRegistry.discover().describe()
    return {
        "ok": all(r.get("ok") for r in rows),
        "entry_point_group": ENTRY_POINT_GROUP,
        "count": len(rows),
        "integrators": rows,
    }


def task_capabilities() -> dict[str, Any]:
    """Return the task-package capability registry."""
    from opl_cancer.plan.task_capabilities import (
        registry_as_list,
        validate_task_capability_registry,
    )

    validation = validate_task_capability_registry()
    return {
        "ok": validation["ok"],
        "summary": validation["summary"],
        "problems": validation["problems"],
        "capabilities": registry_as_list(),
    }


def release_eval(golden_root: str | Path | None = None) -> dict[str, Any]:
    """Run deterministic golden-set release regression checks."""
    from opl_cancer.evaluation.release_golden import run_release_golden_eval

    return run_release_golden_eval(golden_root)
