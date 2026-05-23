"""Test MiniMaxClient — OpenAI-compatible chat/completions schema."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from opl_cancer.llm.base import LLMRequest
from opl_cancer.llm.errors import LLMError
from opl_cancer.llm.minimax_client import MiniMaxClient


@pytest.fixture()
def client() -> MiniMaxClient:
    return MiniMaxClient(api_key="sk-cp-test", base_url="https://api.minimaxi.com/v1")


@respx.mock
async def test_complete_basic(client: MiniMaxClient) -> None:
    respx.post("https://api.minimaxi.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "x",
                "model": "MiniMax-M2.7",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            },
        )
    )
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=128,
    )
    r = await client.complete(req)
    assert r.content == "ok"
    assert r.input_tokens == 4
    assert r.output_tokens == 2


@respx.mock
async def test_json_object_response_format_propagated(client: MiniMaxClient) -> None:
    route = respx.post("https://api.minimaxi.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "x",
                "model": "MiniMax-M2.7",
                "choices": [
                    {
                        "message": {"content": '{"ok": true}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )
    )
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[{"role": "user", "content": "give me JSON"}],
        max_tokens=128,
        response_format={"type": "json_object"},
    )
    await client.complete(req)
    body = route.calls.last.request.read().decode()
    assert "json_object" in body


@respx.mock
async def test_complete_raises_on_2056_errcode(client: MiniMaxClient) -> None:
    respx.post("https://api.minimaxi.com/v1/chat/completions").mock(
        return_value=Response(
            200, json={"base_resp": {"status_code": 2056, "status_msg": "quota exhausted"}}
        )
    )
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
    )
    with pytest.raises(LLMError) as exc:
        await client.complete(req)
    assert "2056" in str(exc.value)


@respx.mock
async def test_complete_raises_on_500(client: MiniMaxClient) -> None:
    respx.post("https://api.minimaxi.com/v1/chat/completions").mock(
        return_value=Response(500)
    )
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
    )
    with pytest.raises(LLMError):
        await client.complete(req)
