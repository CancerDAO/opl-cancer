"""Test LLM client base contract."""
from __future__ import annotations

import pytest

from opl_cancer.llm.base import LLMClient, LLMRequest, LLMResponse, LLMRole
from opl_cancer.llm.errors import LLMError


def test_llm_request_minimum_valid() -> None:
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1024,
    )
    assert req.model == "claude-opus-4-7"
    assert req.max_tokens == 1024


def test_llm_response_carries_token_counts() -> None:
    r = LLMResponse(
        content="hi",
        model="m",
        input_tokens=10,
        output_tokens=5,
        finish_reason="end_turn",
    )
    assert r.input_tokens == 10
    assert r.output_tokens == 5


def test_llm_client_is_abstract() -> None:
    with pytest.raises(TypeError):
        LLMClient()  # type: ignore[abstract]


def test_llm_role_enum() -> None:
    assert LLMRole.USER.value == "user"
    assert LLMRole.SYSTEM.value == "system"
    assert LLMRole.ASSISTANT.value == "assistant"


def test_llm_error_is_runtime_error() -> None:
    e = LLMError("api down")
    assert isinstance(e, RuntimeError)
