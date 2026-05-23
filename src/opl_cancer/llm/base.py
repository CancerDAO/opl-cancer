"""LLM client ABC + request / response schemas.

Hard rules (per memory + spec):
- Failure MUST raise (no silent degradation to keyword stub)
- Reviewer model MUST != Executor model (enforced one layer up in ModelRouter)
- max_tokens chosen per-model ceiling (memory:feedback_max_tokens_model_ceiling)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str


class LLMRequest(BaseModel):
    model: str
    messages: list[dict[str, str]]
    max_tokens: int = Field(ge=1)
    temperature: float = 0.2
    system: str | None = None
    response_format: dict[str, str] | None = None  # e.g. {"type": "json_object"}
    timeout_seconds: float = 120.0


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "end_turn"
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMClient(ABC):
    """Provider-specific HTTPS client. Implementations: AnthropicClaudeClient, MiniMaxClient."""

    provider: str

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Call provider chat API. Must raise LLMError on any failure."""
