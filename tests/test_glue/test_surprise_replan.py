"""D3/ADR-0036 — the mid-run replan RUNTIME: a chased surprise becomes a task.

decide_surprise_followup is the pure discipline; spawn_surprise_replan is the
runtime that acts on it — when a Wave-3 result contradicts the locked forecast or
surfaces a strange-tail anomaly AND carries a testability_path, it writes a replan
task spec the host picks up (a new task/expert that chases the surprise) instead of
only logging it to the failure ledger. The detection (contradicted/anomaly) is LLM
judgment, supplied as input; this runtime enforces the manufactured-novelty guard.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.surprise_replan import spawn_surprise_replan


def test_spawn_chases_contradiction_with_testability_path(tmp_path: Path) -> None:
    out = spawn_surprise_replan(
        tmp_path, hypothesis_id="h1", contradicted=True, anomaly=False,
        testability_path="ctDNA dual-target dynamics at 4 weeks", trigger_detail="forecast said up, data down",
    )
    assert out["should_chase"] is True and out["spawned"] is True
    task_path = Path(out["replan_task_path"])
    assert task_path.is_file()
    task = json.loads(task_path.read_text(encoding="utf-8"))
    assert task["kind"] == "surprise_followup"
    assert task["source_hypothesis_id"] == "h1"
    assert task["trigger"] == "contradicted_forecast"
    assert task["testability_path"] == "ctDNA dual-target dynamics at 4 weeks"
    assert task["status"] == "pending"


def test_spawn_anomaly_trigger_labelled(tmp_path: Path) -> None:
    out = spawn_surprise_replan(
        tmp_path, hypothesis_id="h2", contradicted=False, anomaly=True,
        testability_path="repeat assay on the outlier subclone",
    )
    assert out["spawned"] is True
    task = json.loads(Path(out["replan_task_path"]).read_text(encoding="utf-8"))
    assert task["trigger"] == "strange_tail_anomaly"


def test_spawn_blocks_surprise_with_no_testability_path(tmp_path: Path) -> None:
    out = spawn_surprise_replan(
        tmp_path, hypothesis_id="h3", contradicted=True, anomaly=False, testability_path=None,
    )
    assert out["is_surprise"] is True
    assert out["should_chase"] is False and out["spawned"] is False
    assert out["replan_task_path"] is None
    assert out["blocked_reason"]  # manufactured-novelty guard message
    assert not (tmp_path / "replan").exists()


def test_spawn_noop_when_not_a_surprise(tmp_path: Path) -> None:
    out = spawn_surprise_replan(
        tmp_path, hypothesis_id="h4", contradicted=False, anomaly=False,
        testability_path="irrelevant",
    )
    assert out["is_surprise"] is False and out["spawned"] is False
    assert not (tmp_path / "replan").exists()
