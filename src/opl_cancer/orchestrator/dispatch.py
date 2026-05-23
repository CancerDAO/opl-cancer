"""Wave-based dispatch with main-thread orchestration. Spec §4 + §6.2 + ADR-2026-04-22."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from opl_cancer.plan.schemas import Plan, Task


class ExpertHandler(ABC):
    """Concrete experts (P1+) implement this to be dispatched-to."""

    @abstractmethod
    def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
        ...


def dispatch_wave(
    plan: Plan,
    wave_number: int,
    handlers: dict[str, ExpertHandler],
    context: dict[str, Any],
    max_concurrent: int = 10,
) -> dict[str, dict[str, Any]]:
    """Run all tasks in the given wave. Returns {task_id: executor_output}."""
    wave = next((w for w in plan.waves if w.wave_number == wave_number), None)
    if wave is None:
        raise KeyError(f"wave {wave_number} not in plan")

    tasks_to_run = [t for t in plan.tasks if t.id in wave.task_ids]
    outputs: dict[str, dict[str, Any]] = {}

    for i in range(0, len(tasks_to_run), max_concurrent):
        batch = tasks_to_run[i:i + max_concurrent]
        for task in batch:
            handler = handlers.get(task.expert)
            if handler is None:
                raise KeyError(f"no handler registered for expert {task.expert!r}")
            outputs[task.id] = handler.run_task(task, context)

    return outputs
