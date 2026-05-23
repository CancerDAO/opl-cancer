"""Test async dispatch_wave — real concurrency + depth<=1 + handler missing.

P1-T27 upgrades P0 stub to actual asyncio.gather + Semaphore. The renamed
tautology tests measure wall-time speedup, not just coverage.
"""
import asyncio
import time
from typing import Any

import pytest

from opl_cancer.orchestrator.dispatch import ExpertHandler, dispatch_wave
from opl_cancer.plan.schemas import Plan, Task, WaveAssignment


class _SleepingExpert(ExpertHandler):
    def __init__(self, sleep_s: float) -> None:
        self.sleep_s = sleep_s

    async def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(self.sleep_s)
        return {"task_id": task.id}


def _plan(task_ids: list[str]) -> Plan:
    tasks = [
        Task(id=t, expert="rosa", task_package="x", sub_goal="g", dependencies=[])
        for t in task_ids
    ]
    return Plan(
        run_id="r",
        patient_code="p",
        goal="g",
        waves=[WaveAssignment(wave_number=1, task_ids=task_ids)],
        tasks=tasks,
    )


async def test_dispatch_runs_all_tasks() -> None:
    plan = _plan(["t1", "t2"])
    out = await dispatch_wave(plan, 1, {"rosa": _SleepingExpert(0.01)}, {})
    assert set(out.keys()) == {"t1", "t2"}


async def test_dispatch_actual_concurrency_speedup() -> None:
    """With max_concurrent=5 and 5 tasks @ 0.1s each, wall-time should be <0.3s (parallel)."""
    plan = _plan([f"t{i}" for i in range(5)])
    start = time.perf_counter()
    await dispatch_wave(plan, 1, {"rosa": _SleepingExpert(0.1)}, {}, max_concurrent=5)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.3, f"expected parallel <0.3s, got {elapsed:.3f}s"


async def test_dispatch_respects_max_concurrent() -> None:
    """With max_concurrent=2 and 4 tasks @ 0.05s, wall-time ~2 batches ~0.1s."""
    plan = _plan([f"t{i}" for i in range(4)])
    start = time.perf_counter()
    await dispatch_wave(plan, 1, {"rosa": _SleepingExpert(0.05)}, {}, max_concurrent=2)
    elapsed = time.perf_counter() - start
    assert 0.08 < elapsed < 0.20, f"expected ~0.1s (2 batches), got {elapsed:.3f}s"


async def test_dispatch_handler_missing_raises() -> None:
    plan = _plan(["t1"])
    with pytest.raises(KeyError):
        await dispatch_wave(plan, 1, {}, {})


async def test_dispatch_depth_assert() -> None:
    """Expert handler that tries to re-dispatch must trigger RuntimeError (ADR-2026-04-22)."""
    plan = _plan(["outer"])

    class _Recursive(ExpertHandler):
        async def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
            inner = _plan(["inner"])
            await dispatch_wave(inner, 1, {"rosa": _Recursive()}, {})
            return {}

    with pytest.raises(RuntimeError, match="depth"):
        await dispatch_wave(plan, 1, {"rosa": _Recursive()}, {})
