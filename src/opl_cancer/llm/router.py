"""ModelRouter — dispatches to provider client per models.yaml roster.

Enforces spec §7 G13 (Reviewer model != Executor model) at the routing layer
so concrete experts never accidentally pair same model with itself.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .anthropic_client import AnthropicClaudeClient
from .base import LLMClient
from .errors import LLMError
from .minimax_client import MiniMaxClient


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "models.yaml").exists():
            return parent
    raise FileNotFoundError("models.yaml not found in any parent")


class ModelRouter:
    def __init__(
        self,
        executor: dict[str, Any],
        reviewer_pool: list[dict[str, Any]],
        per_task_routing: dict[str, str] | None = None,
    ) -> None:
        self._executor = executor
        self._reviewer_pool = reviewer_pool
        self._per_task_routing: dict[str, str] = dict(per_task_routing or {})

    @classmethod
    def from_models_yaml(cls, path: Path | None = None) -> ModelRouter:
        p = path or (_repo_root() / "models.yaml")
        cfg = yaml.safe_load(p.read_text())
        executor = cfg["executor_model"]
        reviewer_pool = cfg["reviewer_pool"]
        # Allow a host (e.g. the feynman-opl client, bound to a single model) to
        # bind the executor to a specific provider via OPL_EXECUTOR_PROVIDER.
        # Picks the matching spec from the roster so no second provider is needed.
        # Does NOT change the default; only applies when the env var is set.
        forced = (os.environ.get("OPL_EXECUTOR_PROVIDER") or "").strip().lower()
        if forced and str(executor.get("provider", "")).lower() != forced:
            match = next(
                (m for m in [executor, *reviewer_pool] if str(m.get("provider", "")).lower() == forced),
                None,
            )
            if match is not None:
                executor = match
        return cls(
            executor=executor,
            reviewer_pool=reviewer_pool,
            per_task_routing=cfg.get("per_task_routing") or {},
        )

    @property
    def executor_model_id(self) -> str:
        return str(self._executor["id"])

    @property
    def reviewer_model_ids(self) -> list[str]:
        return [str(m["id"]) for m in self._reviewer_pool]

    def _build_client(self, spec: dict[str, Any]) -> LLMClient:
        provider = spec.get("provider", "")
        api_base = spec.get("api_base", "")
        if provider == "anthropic":
            return AnthropicClaudeClient(base_url=api_base)
        if provider == "minimax":
            return MiniMaxClient(base_url=api_base)
        raise LLMError(f"unknown LLM provider: {provider!r}")

    def executor_client(self) -> LLMClient:
        return self._build_client(self._executor)

    def model_id_for_task(self, task_package: str) -> str:
        """Resolve which model id should handle a task_package.

        Falls back to the default executor model id when the package
        is not listed in per_task_routing.
        """
        return self._per_task_routing.get(task_package, self.executor_model_id)

    def client_for_task(self, task_package: str) -> LLMClient:
        """Build the LLM client that should execute task_package.

        Spec §17.5 P2 — per-task model routing. The executor model is the
        default; any task_package present in models.yaml.per_task_routing
        is routed to its declared model (looked up in executor or reviewer
        pool by id).
        """
        target_id = self.model_id_for_task(task_package)
        if target_id == self.executor_model_id:
            return self._build_client(self._executor)
        for spec in self._reviewer_pool:
            if spec.get("id") == target_id:
                return self._build_client(spec)
        raise LLMError(
            f"per_task_routing target {target_id!r} for task {task_package!r} "
            f"not found in executor or reviewer_pool"
        )

    def reviewer_client_for(
        self, *, executor_model_id: str, reviewer_model_id: str
    ) -> LLMClient:
        if reviewer_model_id == executor_model_id:
            raise LLMError(
                f"G13 violation: reviewer model == executor model ({reviewer_model_id!r})"
            )
        for spec in self._reviewer_pool:
            if spec.get("id") == reviewer_model_id:
                return self._build_client(spec)
        raise LLMError(
            f"reviewer model {reviewer_model_id!r} not in pool {self.reviewer_model_ids}"
        )
