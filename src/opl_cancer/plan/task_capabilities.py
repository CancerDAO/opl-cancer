"""Task-package capability registry.

Experts are the patient-facing mental model. Task packages are the engineering
capabilities. This registry makes that boundary explicit by indexing prompt
files and expert portfolio ownership into a machine-readable map.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import opl_cancer.experts as experts_pkg
from opl_cancer.experts.roster import ROSTER

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TASKS_DIR = _REPO_ROOT / "prompts" / "tasks"


@dataclass(frozen=True)
class TaskCapability:
    task_package: str
    prompt_path: str | None
    prompt_exists: bool
    owners: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _task_prompt_stems() -> set[str]:
    return {p.stem for p in _TASKS_DIR.glob("*.md")}


def _portfolio_owners() -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for mod in pkgutil.iter_modules(experts_pkg.__path__):
        if mod.name.startswith("_") or mod.name in {
            "base",
            "roster",
            "role_taxonomy",
        }:
            continue
        module = importlib.import_module(f"{experts_pkg.__name__}.{mod.name}")
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            portfolio = getattr(obj, "portfolio", None)
            if not portfolio:
                continue
            owner = mod.name.lower()
            for pkg in portfolio:
                owners.setdefault(str(pkg), set()).add(owner)
    for owner, profile in ROSTER.items():
        for pkg in profile.task_package_portfolio:
            owners.setdefault(str(pkg), set()).add(owner)
    return owners


def build_task_capability_registry() -> dict[str, TaskCapability]:
    prompts = _task_prompt_stems()
    owners = _portfolio_owners()
    packages = sorted(prompts | set(owners))
    registry: dict[str, TaskCapability] = {}
    for pkg in packages:
        prompt_path = _TASKS_DIR / f"{pkg}.md"
        rel_prompt = f"prompts/tasks/{pkg}.md"
        registry[pkg] = TaskCapability(
            task_package=pkg,
            prompt_path=rel_prompt if prompt_path.is_file() else None,
            prompt_exists=prompt_path.is_file(),
            owners=sorted(owners.get(pkg, set())),
        )
    return registry


def owners_for_task(task_package: str) -> list[str]:
    capability = build_task_capability_registry().get(task_package)
    return capability.owners if capability else []


def validate_task_capability_registry(
    registry: dict[str, TaskCapability] | None = None,
) -> dict[str, Any]:
    registry = registry or build_task_capability_registry()
    problems: list[dict[str, str]] = []
    for pkg, capability in registry.items():
        if not capability.prompt_exists:
            problems.append({
                "code": "PORTFOLIO_WITHOUT_PROMPT",
                "message": f"{pkg} is owned by {capability.owners} but has no prompt file",
            })
    return {
        "ok": not problems,
        "problems": problems,
        "summary": {
            "count": len(registry),
            "owned": sum(1 for c in registry.values() if c.owners),
            "unowned": sum(1 for c in registry.values() if not c.owners),
            "missing_prompt": sum(1 for c in registry.values() if not c.prompt_exists),
        },
    }


def registry_as_list() -> list[dict[str, Any]]:
    return [cap.to_dict() for cap in build_task_capability_registry().values()]
