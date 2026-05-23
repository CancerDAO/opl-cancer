"""Iter 13 (v1.0.5) — per-task model routing.

Spec §17.5 P2: ModelRouter.client_for_task(task_package) returns the
provider client declared for that task in models.yaml.per_task_routing,
falling back to the default executor model.
"""
from __future__ import annotations

import pytest

from opl_cancer.llm.anthropic_client import AnthropicClaudeClient
from opl_cancer.llm.errors import LLMError
from opl_cancer.llm.minimax_client import MiniMaxClient
from opl_cancer.llm.router import ModelRouter


def _router(monkeypatch: pytest.MonkeyPatch) -> ModelRouter:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("MINIMAX_API_KEY", "test")
    return ModelRouter.from_models_yaml()


def test_client_for_task_routes_literature_synthesis_to_minimax(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """literature_synthesis is mapped to minimax-m2-7 in models.yaml."""
    r = _router(monkeypatch)
    assert r.model_id_for_task("literature_synthesis") == "minimax-m2-7"
    client = r.client_for_task("literature_synthesis")
    assert isinstance(client, MiniMaxClient)


def test_client_for_task_routes_hypothesis_generation_to_opus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hypothesis_generation stays on the default Opus executor."""
    r = _router(monkeypatch)
    assert r.model_id_for_task("hypothesis_generation") == "claude-opus-4-7"
    client = r.client_for_task("hypothesis_generation")
    assert isinstance(client, AnthropicClaudeClient)


def test_client_for_task_falls_back_to_executor_for_unknown_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown task_package -> default executor model (Opus)."""
    r = _router(monkeypatch)
    assert r.model_id_for_task("totally_unknown_task") == r.executor_model_id
    client = r.client_for_task("totally_unknown_task")
    assert isinstance(client, AnthropicClaudeClient)


def test_client_for_task_raises_when_target_missing_from_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If per_task_routing names a model id absent from executor + pool, raise."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = ModelRouter(
        executor={
            "id": "claude-opus-4-7",
            "provider": "anthropic",
            "api_base": "https://api.anthropic.com",
        },
        reviewer_pool=[],
        per_task_routing={"bogus_task": "ghost-model-x"},
    )
    with pytest.raises(LLMError) as exc:
        r.client_for_task("bogus_task")
    assert "ghost-model-x" in str(exc.value)
