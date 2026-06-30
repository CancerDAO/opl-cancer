from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.glue.run_events import (
    append_run_event,
    iter_run_events,
    load_run_checkpoint,
    summarize_run_events,
    write_run_checkpoint,
)


def test_run_event_append_hash_and_filter(tmp_path: Path) -> None:
    run_root = tmp_path / "P" / "triggers" / "r1"
    first = append_run_event(
        run_root,
        "plan.started",
        phase="planning",
        payload={"x": 1},
        at="2026-06-30T00:00:00+00:00",
    )
    second = append_run_event(
        run_root,
        "wave1.pending",
        phase="wave1",
        severity="warn",
        at="2026-06-30T00:01:00+00:00",
    )

    assert first["event_hash"].startswith("sha256:")
    assert len(first["event_id"]) == 16
    all_events = list(iter_run_events(run_root))
    assert [e["event_type"] for e in all_events] == ["plan.started", "wave1.pending"]
    assert list(iter_run_events(run_root, phase="wave1")) == [second]

    summary = summarize_run_events(run_root)
    assert summary["count"] == 2
    assert summary["by_type"]["plan.started"] == 1
    assert summary["by_phase"]["wave1"] == 1
    assert summary["last_event"]["event_type"] == "wave1.pending"


def test_cli_events_emit_and_list_json(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()
    r = CliRunner()
    emitted = r.invoke(
        main,
        [
            "events",
            "--patient", str(patient),
            "--run-id", "r1",
            "--emit", "operator.note",
            "--phase", "planning",
            "--payload-json", '{"note":"hello"}',
            "--json",
        ],
    )
    assert emitted.exit_code == 0, emitted.output
    assert json.loads(emitted.output)["event"]["payload"]["note"] == "hello"

    listed = r.invoke(main, ["events", "--patient", str(patient), "--run-id", "r1", "--json"])
    assert listed.exit_code == 0, listed.output
    payload = json.loads(listed.output)
    assert payload["summary"]["count"] == 1
    assert payload["events"][0]["event_type"] == "operator.note"


def test_checkpoint_write_persists_latest_and_event(tmp_path: Path) -> None:
    run_root = tmp_path / "P" / "triggers" / "r1"
    checkpoint = write_run_checkpoint(
        run_root,
        phase="wave2",
        reason="waiting for child validation",
        payload={"frontier": "H2"},
        at="2026-06-30T00:02:00+00:00",
    )

    assert checkpoint["schema"] == "opl.run_checkpoint.v1"
    assert checkpoint["payload"]["frontier"] == "H2"
    assert load_run_checkpoint(run_root) == checkpoint
    events = list(iter_run_events(run_root))
    assert events[-1]["event_type"] == "checkpoint.saved"
    assert events[-1]["payload"]["reason"] == "waiting for child validation"


def test_cli_checkpoint_write_and_read_json(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()
    r = CliRunner()
    written = r.invoke(
        main,
        [
            "checkpoint",
            "--patient", str(patient),
            "--run-id", "r1",
            "--write",
            "--phase", "wave3",
            "--reason", "compute backend paused",
            "--payload-json", '{"next":"run wave3"}',
            "--json",
        ],
    )
    assert written.exit_code == 0, written.output
    assert json.loads(written.output)["checkpoint"]["payload"]["next"] == "run wave3"

    read = r.invoke(main, ["checkpoint", "--patient", str(patient), "--run-id", "r1", "--json"])
    assert read.exit_code == 0, read.output
    assert json.loads(read.output)["checkpoint"]["reason"] == "compute backend paused"


def test_cli_plan_writes_manifest_event(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()
    r = CliRunner().invoke(
        main,
        [
            "plan",
            "--patient", str(patient),
            "--goal", "next line",
            "--run-id", "r1",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    events = list(iter_run_events(patient / "triggers" / "r1"))
    assert [e["event_type"] for e in events] == ["plan.manifest_written"]
    assert events[0]["payload"]["run_token_present"] is True


def test_observe_includes_run_event_summary(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    run_root = patient / "triggers" / "r1"
    append_run_event(run_root, "plan.manifest_written", phase="planning")
    write_run_checkpoint(run_root, phase="planning", reason="resume at plan")

    out = CliRunner().invoke(
        main, ["observe", "--patient", str(patient), "--run-id", "r1", "--json"]
    )
    assert out.exit_code == 0, out.output
    payload = json.loads(out.output)
    assert payload["events"]["count"] == 2
    assert payload["events"]["last_event"]["event_type"] == "checkpoint.saved"
    assert payload["checkpoint"]["reason"] == "resume at plan"
