"""MiniMax MiniMax-M2.7 client (OpenAI-compatible chat/completions).

Per memory:reference_minimax_llm:
- endpoint https://api.minimaxi.com/v1/chat/completions
- key prefix sk-cp-...
- max_tokens upper ceiling 196608 (recommended <= 96000)
- response_format={"type":"json_object"} forces strict JSON output
- error code 2056 in body.base_resp.status_code == quota exhausted
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from .base import LLMClient, LLMRequest, LLMResponse
from .errors import LLMError, LLMQuotaError, LLMResponseParseError


class MiniMaxClient(LLMClient):
    provider = "minimax"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimaxi.com/v1",
    ) -> None:
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        if not self.api_key:
            raise LLMError("MINIMAX_API_KEY not set and api_key not provided")
        self.base_url = base_url.rstrip("/")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        messages = list(request.messages)
        if request.system is not None:
            # OpenAI-style: prepend system message
            messages = [{"role": "system", "content": request.system}, *messages]

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": min(request.max_tokens, 196608),
            "temperature": request.temperature,
        }
        if request.response_format is not None:
            payload["response_format"] = request.response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as http:
                resp = await http.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise LLMError(f"minimax transport error: {e}") from e

        if resp.status_code == 429:
            raise LLMQuotaError(f"minimax rate-limit: {resp.text}")
        if resp.status_code >= 400:
            raise LLMError(f"minimax HTTP {resp.status_code}: {resp.text}")

        try:
            body = resp.json()
        except ValueError as e:
            raise LLMResponseParseError(f"minimax non-JSON response: {resp.text!r}") from e

        # MiniMax embeds business errors in body.base_resp even on HTTP 200
        base = body.get("base_resp", {}) or {}
        if base.get("status_code", 0) not in (0, None):
            code = base["status_code"]
            msg = base.get("status_msg", "")
            if code == 2056:
                raise LLMQuotaError(f"minimax errcode 2056 (quota): {msg}")
            raise LLMError(f"minimax errcode {code}: {msg}")

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
            usage = body.get("usage", {})
            return LLMResponse(
                content=content,
                model=body.get("model", request.model),
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                finish_reason=choice.get("finish_reason", "stop"),
                raw=body,
            )
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMResponseParseError(f"minimax response unparseable: {body!r}") from e
