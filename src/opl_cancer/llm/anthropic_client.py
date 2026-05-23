"""Anthropic Claude API client (Messages endpoint).

Docs: https://docs.anthropic.com/en/api/messages
Spec §17.5 P2 — Claude Opus 4.7 default for hypothesis / synthesis / reasoning.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from .base import LLMClient, LLMRequest, LLMResponse
from .errors import LLMError, LLMQuotaError, LLMResponseParseError


class AnthropicClaudeClient(LLMClient):
    provider = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        api_version: str = "2023-06-01",
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY not set and api_key not provided")
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.system is not None:
            payload["system"] = request.system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as http:
                resp = await http.post(
                    f"{self.base_url}/v1/messages", json=payload, headers=headers
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise LLMError(f"anthropic transport error: {e}") from e

        if resp.status_code == 429:
            raise LLMQuotaError(f"anthropic rate-limit: {resp.text}")
        if resp.status_code >= 400:
            raise LLMError(f"anthropic HTTP {resp.status_code}: {resp.text}")

        try:
            body = resp.json()
            text_blocks = [
                b["text"] for b in body.get("content", []) if b.get("type") == "text"
            ]
            content = "".join(text_blocks)
            usage = body.get("usage", {})
            return LLMResponse(
                content=content,
                model=body.get("model", request.model),
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                finish_reason=body.get("stop_reason", "end_turn"),
                raw=body,
            )
        except (KeyError, ValueError, TypeError) as e:
            raise LLMResponseParseError(
                f"anthropic response unparseable: {resp.text!r}"
            ) from e
