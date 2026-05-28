"""v2.1 P0-#6: task_package fail-fast at plan emit.

Asserts every ``task.task_package`` is the stem of a file in
``prompts/tasks/``. Unknown names raise ``UnknownTaskPackage`` with a
Levenshtein Did-you-mean top-3 hint.

ADR-0021 invariant: a typoed task package would otherwise reach the
runner, which silently degrades to a "no prompt found" path. We want
the plan to refuse to emit, not the runner to fail in a confusing place.

The list of available task packages is computed at runtime by globbing
``prompts/tasks/*.md`` — no hardcoded count. As packages are added or
renamed, this validator picks them up automatically.
"""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TASKS_DIR = _REPO_ROOT / "prompts" / "tasks"


class UnknownTaskPackage(ValueError):
    """Raised when a plan references a task package not in prompts/tasks/."""


def list_packages() -> list[str]:
    """Return sorted list of available task package stems."""
    return sorted(p.stem for p in _TASKS_DIR.glob("*.md"))


def validate_task_packages(tasks: Iterable[dict]) -> None:
    """Validate every task in ``tasks`` references a known task package.

    Each task dict must have a ``task_package`` key. Missing or unknown
    values raise ``UnknownTaskPackage`` with a Did-you-mean suggestion.
    """
    pkgs = set(list_packages())
    for t in tasks:
        name = t.get("task_package") if isinstance(t, dict) else getattr(t, "task_package", None)
        if name in pkgs:
            continue
        suggestions = difflib.get_close_matches(name or "", pkgs, n=3, cutoff=0.5)
        hint = f" Did you mean: {suggestions}?" if suggestions else ""
        sample = sorted(pkgs)[:5]
        task_id = (
            t.get("task_id") if isinstance(t, dict) else getattr(t, "id", "unknown")
        )
        raise UnknownTaskPackage(
            f"task {task_id!r} references unknown package {name!r}.{hint} "
            f"Available (first 5 of {len(pkgs)}): {sample}…"
        )
