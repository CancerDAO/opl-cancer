"""ModelRouter — dispatches to provider client per models.yaml roster.

Enforces spec §7 G13 (Reviewer model != Executor model) at the routing layer
so concrete experts never accidentally pair same model with itself.
"""
from __future__ import annotations

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
    ) -> None:
        self._executor = executor
        self._reviewer_pool = reviewer_pool

    @classmethod
    def from_models_yaml(cls, path: Path | None = None) -> ModelRouter:
        p = path or (_repo_root() / "models.yaml")
        cfg = yaml.safe_load(p.read_text())
        return cls(executor=cfg["executor_model"], reviewer_pool=cfg["reviewer_pool"])

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
