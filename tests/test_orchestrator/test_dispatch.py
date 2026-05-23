"""Test wave-based dispatch framework — spec §4 + §6.2."""
from typing import Any

import pytest

from opl_cancer.orchestrator.dispatch import ExpertHandler, dispatch_wave
from opl_cancer.plan.schemas import Plan, Task, WaveAssignment


class _RecordingExpert(ExpertHandler):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(task.id)
        return {"task_id": task.id, "status": "done"}


def _make_plan(task_ids: list[str], wave_num: int = 1) -> Plan:
    tasks = [
        Task(id=tid, expert="rosa", task_package="x", sub_goal="g", dependencies=[])
        for tid in task_ids
    ]
    return Plan(
        run_id="r", patient_code="p", goal="g",
        waves=[WaveAssignment(wave_number=wave_num, task_ids=task_ids)],
        tasks=tasks,
    )


def test_dispatch_wave_runs_all_tasks_in_wave() -> None:
    plan = _make_plan(["t1", "t2", "t3"])
    expert = _RecordingExpert()
    handlers = {"rosa": expert}
    outputs = dispatch_wave(plan, wave_number=1, handlers=handlers, context={})
    assert set(outputs.keys()) == {"t1", "t2", "t3"}
    assert set(expert.calls) == {"t1", "t2", "t3"}


def test_dispatch_wave_respects_concurrency_limit() -> None:
    plan = _make_plan([f"t{i}" for i in range(15)])
    expert = _RecordingExpert()
    handlers = {"rosa": expert}
    outputs = dispatch_wave(plan, wave_number=1, handlers=handlers, context={}, max_concurrent=10)
    assert len(outputs) == 15


def test_dispatch_wave_handler_missing_raises() -> None:
    plan = _make_plan(["t1"])
    with pytest.raises(KeyError):
        dispatch_wave(plan, wave_number=1, handlers={}, context={})
