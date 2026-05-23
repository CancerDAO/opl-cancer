"""Test ModelRouter — load models.yaml, enforce Reviewer != Executor (G13)."""
from __future__ import annotations

import pytest

from opl_cancer.llm.anthropic_client import AnthropicClaudeClient
from opl_cancer.llm.errors import LLMError
from opl_cancer.llm.minimax_client import MiniMaxClient
from opl_cancer.llm.router import ModelRouter


def test_router_loads_models_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("MINIMAX_API_KEY", "test")
    r = ModelRouter.from_models_yaml()
    assert r.executor_model_id == "claude-opus-4-7"
    assert "minimax-m2-7" in r.reviewer_model_ids


def test_router_executor_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("MINIMAX_API_KEY", "test")
    r = ModelRouter.from_models_yaml()
    client = r.executor_client()
    assert isinstance(client, AnthropicClaudeClient)


def test_router_reviewer_for_executor_raises_when_same(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G13: requesting a reviewer whose model id == executor must raise."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("MINIMAX_API_KEY", "test")
    r = ModelRouter.from_models_yaml()
    with pytest.raises(LLMError) as exc:
        r.reviewer_client_for(
            executor_model_id="claude-opus-4-7",
            reviewer_model_id="claude-opus-4-7",
        )
    assert "G13" in str(exc.value)


def test_router_reviewer_picks_minimax(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("MINIMAX_API_KEY", "test")
    r = ModelRouter.from_models_yaml()
    client = r.reviewer_client_for(
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    assert isinstance(client, MiniMaxClient)


def test_router_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = ModelRouter(
        executor={"id": "x", "provider": "unknown", "api_base": "https://x"},
        reviewer_pool=[],
    )
    with pytest.raises(LLMError):
        r.executor_client()
