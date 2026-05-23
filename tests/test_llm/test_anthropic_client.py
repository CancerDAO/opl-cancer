"""Test AnthropicClaudeClient — httpx call, error handling, parse."""
from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Response

from opl_cancer.llm.anthropic_client import AnthropicClaudeClient
from opl_cancer.llm.base import LLMRequest
from opl_cancer.llm.errors import LLMError, LLMQuotaError


@pytest.fixture()
def client() -> AnthropicClaudeClient:
    return AnthropicClaudeClient(api_key="test-key", base_url="https://api.anthropic.com")


@respx.mock
async def test_complete_returns_content(client: AnthropicClaudeClient) -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json={
                "content": [{"type": "text", "text": "hello back"}],
                "model": "claude-opus-4-7",
                "usage": {"input_tokens": 5, "output_tokens": 3},
                "stop_reason": "end_turn",
            },
        )
    )
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=128,
    )
    r = await client.complete(req)
    assert r.content == "hello back"
    assert r.input_tokens == 5
    assert r.output_tokens == 3


@respx.mock
async def test_complete_raises_on_500(client: AnthropicClaudeClient) -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(500, json={"error": "internal"})
    )
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
    )
    with pytest.raises(LLMError):
        await client.complete(req)


@respx.mock
async def test_complete_raises_quota_on_429(client: AnthropicClaudeClient) -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(429, json={"error": "rate_limit"})
    )
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
    )
    with pytest.raises(LLMQuotaError):
        await client.complete(req)


@respx.mock
async def test_complete_raises_on_network_error(client: AnthropicClaudeClient) -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        side_effect=ConnectError("dns fail")
    )
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
    )
    with pytest.raises(LLMError):
        await client.complete(req)


@respx.mock
async def test_system_prompt_propagated(client: AnthropicClaudeClient) -> None:
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json={
                "content": [{"type": "text", "text": "ok"}],
                "model": "m",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "stop_reason": "end_turn",
            },
        )
    )
    req = LLMRequest(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
        system="You are Sid the PI.",
    )
    await client.complete(req)
    body = route.calls.last.request.read().decode()
    assert "Sid the PI" in body
