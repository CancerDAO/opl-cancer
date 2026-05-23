"""Wave-based dispatch — async + concurrency-bounded + depth<=1 assert.

Spec §4 + §6.2 + ADR-2026-04-22 (main-thread only). Closes P0 loop-back items:
- actual concurrency via asyncio.gather + Semaphore(max_concurrent)
- depth<=1 assert (Expert handlers MUST NOT dispatch further waves)
"""
from __future__ import annotations

import asyncio
import contextvars
from abc import ABC, abstractmethod
from typing import Any

from opl_cancer.plan.schemas import Plan, Task


_DISPATCH_DEPTH: contextvars.ContextVar[int] = contextvars.ContextVar(
    "opl_dispatch_depth", default=0
)


class ExpertHandler(ABC):
    """Concrete experts (P1+) implement this to be dispatched-to.

    Per ADR-2026-04-22 main-thread-only: ``run_task`` is async (LLM + integrator
    network I/O), but handlers MUST NOT re-enter :func:`dispatch_wave` themselves
    — depth>1 raises ``RuntimeError``.
    """

    @abstractmethod
    async def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
        ...


async def dispatch_wave(
    plan: Plan,
    wave_number: int,
    handlers: dict[str, ExpertHandler],
    context: dict[str, Any],
    max_concurrent: int = 10,
) -> dict[str, dict[str, Any]]:
    """Run all tasks in the given wave concurrently.

    Returns ``{task_id: handler_output}``. Concurrency capped by
    ``max_concurrent`` via :class:`asyncio.Semaphore`. Depth tracked via
    :mod:`contextvars` so any handler that tries to call ``dispatch_wave``
    again raises ``RuntimeError`` (ADR-0002 main-thread-only).
    """
    depth = _DISPATCH_DEPTH.get()
    if depth >= 1:
        raise RuntimeError(
            "dispatch_wave depth>1 detected — ADR-2026-04-22 main-thread-only "
            "violated. Expert handlers must NOT call dispatch_wave themselves."
        )

    wave = next((w for w in plan.waves if w.wave_number == wave_number), None)
    if wave is None:
        raise KeyError(f"wave {wave_number} not in plan")

    tasks_to_run = [t for t in plan.tasks if t.id in wave.task_ids]
    sem = asyncio.Semaphore(max_concurrent)

    async def _run(task: Task) -> tuple[str, dict[str, Any]]:
        handler = handlers.get(task.expert)
        if handler is None:
            raise KeyError(f"no handler registered for expert {task.expert!r}")
        async with sem:
            token = _DISPATCH_DEPTH.set(depth + 1)
            try:
                out = await handler.run_task(task, context)
            finally:
                _DISPATCH_DEPTH.reset(token)
            return task.id, out

    results = await asyncio.gather(*[_run(t) for t in tasks_to_run])
    return dict(results)
