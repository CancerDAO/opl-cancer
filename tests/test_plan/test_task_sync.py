"""v2.3 P2-#22 — TaskCreate / TaskUpdate sync helper tests."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from opl_cancer.plan.task_sync import (
    TASKCREATE_ENV_FLAG,
    emit_plan_tasks_for_waves,
    is_taskcreate_enabled,
    log_task_create,
    log_task_update,
    mark_wave_completed,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TASKCREATE_ENV_FLAG, raising=False)


def test_disabled_by_default() -> None:
    assert is_taskcreate_enabled() is False


def test_enabled_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TASKCREATE_ENV_FLAG, "1")
    assert is_taskcreate_enabled() is True


def test_log_task_create_appends_jsonl(tmp_path: Path) -> None:
    log_task_create(
        run_dir=tmp_path, wave=1, subject="Wave 1 execution",
        description="OPL Wave 1 pipeline",
    )
    log_path = tmp_path / "task_sync.jsonl"
    assert log_path.is_file()
    line = log_path.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["kind"] == "TaskCreate"
    assert rec["wave"] == 1
    assert rec["enabled"] is False


def test_log_task_update(tmp_path: Path) -> None:
    log_task_update(run_dir=tmp_path, wave=2, status="completed")
    lines = (tmp_path / "task_sync.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    rec = json.loads(lines[0])
    assert rec["kind"] == "TaskUpdate"
    assert rec["status"] == "completed"


def test_emit_plan_tasks_for_waves(tmp_path: Path) -> None:
    records = emit_plan_tasks_for_waves(
        run_dir=tmp_path, waves=[1, 2, 3, 4, 5, 6],
        plan_summary="Full session",
    )
    assert len(records) == 6
    lines = (tmp_path / "task_sync.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    assert len(lines) == 6
    for ln in lines:
        rec = json.loads(ln)
        assert rec["kind"] == "TaskCreate"
        assert rec["wave"] in {1, 2, 3, 4, 5, 6}


def test_mark_wave_completed_appends(tmp_path: Path) -> None:
    log_task_create(run_dir=tmp_path, wave=1, subject="w1")
    mark_wave_completed(run_dir=tmp_path, wave=1)
    lines = (tmp_path / "task_sync.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    assert len(lines) == 2
    last = json.loads(lines[-1])
    assert last["kind"] == "TaskUpdate"
    assert last["status"] == "completed"


def test_enabled_flag_propagates_into_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(TASKCREATE_ENV_FLAG, "1")
    log_task_create(run_dir=tmp_path, wave=1, subject="w1")
    rec = json.loads((tmp_path / "task_sync.jsonl").read_text().strip())
    assert rec["enabled"] is True
