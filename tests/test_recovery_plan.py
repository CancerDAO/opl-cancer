from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.glue.recovery import SCHEMA, build_recovery_plan
from opl_cancer.glue.run_events import append_run_event, write_run_checkpoint


def test_recovery_plan_blocks_missing_run(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()

    plan = build_recovery_plan(
        patient,
        "r1",
        validation_problems=[
            {"severity": "error", "code": "RUN_MISSING", "message": "missing"}
        ],
    )

    assert plan["schema"] == SCHEMA
    assert plan["ok"] is False
    assert plan["status"] == "blocked"
    assert plan["next_actions"][0]["code"] == "check_run_id_or_plan"


def test_recovery_plan_prefers_validation_repair(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    run_root = patient / "triggers" / "r1"
    run_root.mkdir(parents=True)

    plan = build_recovery_plan(
        patient,
        "r1",
        validation_problems=[
            {"severity": "error", "code": "NO_RUN_TOKEN", "message": "token missing"}
        ],
    )

    assert plan["status"] == "needs_repair"
    assert plan["next_actions"][0]["code"] == "rerun_plan"


def test_recovery_plan_uses_checkpoint_next_action(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    run_root = patient / "triggers" / "r1"
    write_run_checkpoint(
        run_root,
        phase="wave3",
        reason="compute paused",
        payload={"next": "run Wave 3 state-check after compute artifacts land"},
    )

    plan = build_recovery_plan(
        patient,
        "r1",
        projection={"outstanding_waves": [3]},
        validation_problems=[],
    )

    assert plan["status"] == "ready_to_resume"
    assert plan["checkpoint"]["reason"] == "compute paused"
    assert plan["next_actions"][0]["code"] == "resume_checkpoint_next"
    assert "Wave 3" in plan["next_actions"][0]["label"]


def test_recovery_plan_triages_error_event(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    run_root = patient / "triggers" / "r1"
    append_run_event(run_root, "wave2.failed", severity="error", payload={"reason": "x"})

    plan = build_recovery_plan(patient, "r1", validation_problems=[])

    assert plan["status"] == "needs_triage"
    assert plan["latest_error_events"][0]["event_type"] == "wave2.failed"
    assert plan["next_actions"][0]["code"] == "triage_last_error_event"


def test_cli_recovery_plan_json(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()

    result = CliRunner().invoke(
        main,
        ["recovery-plan", "--patient", str(patient), "--run-id", "r1", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == SCHEMA
    assert payload["status"] == "blocked"

