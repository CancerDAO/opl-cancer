"""Deterministic failure-recovery planning for OPL runs.

Recovery is deliberately separate from execution. This module reads durable
state and proposes the next operator action; it never dispatches experts, runs a
wave, mutates artifacts, or "fixes" clinical content.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opl_cancer.glue.run_events import (
    iter_run_events,
    load_run_checkpoint,
    summarize_run_events,
)

SCHEMA = "opl.recovery_plan.v1"


def _action(
    code: str,
    label: str,
    *,
    reason: str,
    command: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "label": label,
        "reason": reason,
        "command": command,
    }


def _command(name: str, patient_dir: Path, run_id: str, *extra: str) -> str:
    args = " ".join(extra)
    suffix = f" {args}" if args else ""
    return f"opl-cancer {name} --patient {patient_dir} --run-id {run_id}{suffix}"


def _validation_action(problem: dict[str, str], patient_dir: Path, run_id: str) -> dict[str, Any]:
    code = problem.get("code", "UNKNOWN")
    message = problem.get("message", "")
    if code in {"RUN_MISSING", "NO_MANIFEST", "NO_RUN_TOKEN"}:
        return _action(
            "rerun_plan",
            "Recreate or rerun the plan step for this run_id.",
            reason=message,
            command=_command("plan", patient_dir, run_id, '--goal "<patient goal>"'),
        )
    if code == "MANIFEST_PLAN_DRIFT":
        return _action(
            "explicit_replan",
            "Resolve manifest/plan drift with an explicit replan before continuing.",
            reason=message,
            command=_command("plan", patient_dir, run_id, '--goal "<confirmed goal>"'),
        )
    if code == "ATTESTED_WITHOUT_BRIEF":
        return _action(
            "rerun_delivery",
            "Regenerate and finalize delivery artifacts, then attest again.",
            reason=message,
            command=f"opl-cancer deliver --patient-dir {patient_dir} --run-id {run_id} --finalize",
        )
    if code == "DELIVERED_NOT_ATTESTED":
        return _action(
            "attest_delivery",
            "Run delivery attestation before treating the brief as complete.",
            reason=message,
            command=f"opl-cancer attest --patient-dir {patient_dir} --run-id {run_id}",
        )
    if code in {"DELIVERED_NO_LEDGER", "DELIVERED_EMPTY_LEDGER"}:
        return _action(
            "rebuild_delivery_memory",
            "Rerun finalize after fixing the Project Memory ledger write.",
            reason=message,
            command=f"opl-cancer deliver --patient-dir {patient_dir} --run-id {run_id} --finalize",
        )
    if code == "DELIVERED_WITH_OUTSTANDING_WAVES":
        return _action(
            "complete_missing_waves",
            "Complete outstanding planned waves before attempting delivery again.",
            reason=message,
            command=_command("observe", patient_dir, run_id, "--json"),
        )
    if code == "DEPTH_BUDGET_EXCEEDED":
        return _action(
            "stop_reentry_and_replan",
            "Stop deeper re-entry and create an explicit replan if more depth is needed.",
            reason=message,
            command=_command("deepen", patient_dir, run_id, "--target <hypothesis_id>"),
        )
    return _action(
        "inspect_validation_problem",
        "Inspect and repair this validation problem before continuing.",
        reason=message or code,
        command=_command("validate", patient_dir, run_id, "--json"),
    )


def _checkpoint_action(checkpoint: dict[str, Any], patient_dir: Path, run_id: str) -> dict[str, Any]:
    payload = checkpoint.get("payload") if isinstance(checkpoint.get("payload"), dict) else {}
    explicit_next = payload.get("next")
    phase = checkpoint.get("phase")
    if explicit_next:
        return _action(
            "resume_checkpoint_next",
            str(explicit_next),
            reason=str(checkpoint.get("reason") or "checkpoint resume"),
        )
    phase_cmds = {
        "planning": _command("observe", patient_dir, run_id, "--json"),
        "wave1": f"opl-cancer wave1 --patient-dir {patient_dir} --run-id {run_id}",
        "wave2": f"opl-cancer wave2 --patient-dir {patient_dir} --run-id {run_id}",
        "wave3": f"opl-cancer wave3 --patient-dir {patient_dir} --run-id {run_id}",
        "wave4": f"opl-cancer wave4 --patient-dir {patient_dir} --run-id {run_id}",
        "delivery": f"opl-cancer deliver --patient-dir {patient_dir} --run-id {run_id} --finalize",
    }
    return _action(
        "resume_from_checkpoint",
        f"Resume from checkpoint phase {phase or '(unset)'}.",
        reason=str(checkpoint.get("reason") or "checkpoint resume"),
        command=phase_cmds.get(str(phase), _command("observe", patient_dir, run_id, "--json")),
    )


def _next_wave_action(
    outstanding_waves: list[Any],
    patient_dir: Path,
    run_id: str,
) -> dict[str, Any] | None:
    if not outstanding_waves:
        return None
    wave = sorted(int(w) for w in outstanding_waves if str(w).isdigit())[0]
    if wave in {1, 2, 3, 4}:
        return _action(
            f"complete_wave_{wave}",
            f"Dispatch host artifacts for Wave {wave}, then run its state-check.",
            reason="observe reports planned wave artifacts are still missing",
            command=f"opl-cancer wave{wave} --patient-dir {patient_dir} --run-id {run_id}",
        )
    if wave == 5:
        return _action(
            "complete_delivery",
            "Finalize delivery after prior waves are complete.",
            reason="observe reports delivery is still outstanding",
            command=f"opl-cancer deliver --patient-dir {patient_dir} --run-id {run_id} --finalize",
        )
    return _action(
        "inspect_outstanding_wave",
        f"Inspect outstanding planned wave {wave}.",
        reason="observe reports an outstanding wave outside the standard state-check set",
        command=_command("observe", patient_dir, run_id, "--json"),
    )


def build_recovery_plan(
    patient_dir: str | Path,
    run_id: str,
    *,
    projection: dict[str, Any] | None = None,
    validation_problems: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic recovery plan for one run."""
    patient_dir = Path(patient_dir)
    run_root = patient_dir / "triggers" / run_id
    checkpoint = load_run_checkpoint(run_root)
    event_summary = summarize_run_events(run_root)
    events = list(iter_run_events(run_root))
    error_events = [
        e for e in events
        if e.get("severity") == "error" or str(e.get("event_type", "")).endswith(".failed")
    ][-5:]
    validation_problems = validation_problems or []
    errors = [p for p in validation_problems if p.get("severity") == "error"]
    warnings = [p for p in validation_problems if p.get("severity") == "warn"]

    actions: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []

    if not run_root.exists():
        blockers.append({"code": "RUN_MISSING", "message": f"no run directory at {run_root}"})
        actions.append(
            _action(
                "check_run_id_or_plan",
                "Check the run_id or start planning this run.",
                reason="run directory is missing",
                command=_command("plan", patient_dir, run_id, '--goal "<patient goal>"'),
            )
        )
        status = "blocked"
    elif errors:
        actions.extend(_validation_action(p, patient_dir, run_id) for p in errors)
        status = "needs_repair"
    elif checkpoint:
        actions.append(_checkpoint_action(checkpoint, patient_dir, run_id))
        status = "ready_to_resume"
    elif error_events:
        latest = error_events[-1]
        actions.append(
            _action(
                "triage_last_error_event",
                "Inspect the latest error event and write a checkpoint before retrying.",
                reason=str(latest.get("event_type")),
                command=_command("events", patient_dir, run_id, "--limit 5 --json"),
            )
        )
        status = "needs_triage"
    elif projection and projection.get("attested") and projection.get("delivered"):
        actions.append(
            _action(
                "no_recovery_needed",
                "Run is delivered and attested.",
                reason="observe reports delivery and attestation are complete",
            )
        )
        status = "complete"
    else:
        next_wave = _next_wave_action(
            list(projection.get("outstanding_waves", [])) if projection else [],
            patient_dir,
            run_id,
        )
        if next_wave:
            actions.append(next_wave)
        else:
            actions.append(
                _action(
                    "observe_state",
                    "Observe run state and continue the next planned beat.",
                    reason="no checkpoint or validation error identifies a narrower recovery path",
                    command=_command("observe", patient_dir, run_id, "--json"),
                )
            )
        status = "needs_progress"

    return {
        "schema": SCHEMA,
        "ok": status != "blocked",
        "run_id": run_id,
        "status": status,
        "run_root": str(run_root),
        "checkpoint": checkpoint,
        "event_summary": event_summary,
        "latest_error_events": error_events,
        "validation": {
            "errors": len(errors),
            "warnings": len(warnings),
            "problems": validation_problems,
        },
        "blockers": blockers,
        "next_actions": actions,
    }

