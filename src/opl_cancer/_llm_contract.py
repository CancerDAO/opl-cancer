"""Transitional LLM contract shim — KEEPS orchestrator/ and evolution/ IMPORTABLE.

Background (docs/iteration/HARNESS_SPLIT_PRD.md):
The patient-delivery path no longer calls LLMs internally — the host agent is the
executor. The provider clients (router / minimax_client / anthropic_client) were
deleted with the ``opl_cancer.llm`` package. However ``orchestrator/*`` and
``evolution/*`` (the evolution-engine / G13-redefinition phase, NOT the patient
path) still reference the request/response/client *contract types* for their
type annotations and ``LLMRequest(...)`` construction.

This module preserves ONLY those Pydantic schemas + the abstract client +
error types — with NO provider implementation and NO network code — so that
``import opl_cancer`` and the patient CLI keep working after llm/ deletion.

TODO(decouple-phase): the next phase fully decouples orchestrator/evolution from
the patient package. When that lands, this shim (and the orchestrator/evolution
imports of it) should be moved into the evolution engine's own module tree and
this file deleted from the patient package. Do NOT add a provider client here —
the patient path must never call an LLM internally (no-silent-fallback policy,
HARNESS_SPLIT_PRD red line).
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
    """Provider-specific HTTPS client contract.

    No concrete implementation lives in the patient package anymore — the
    evolution engine supplies its own client at call time.
    """

    provider: str

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Call provider chat API. Must raise LLMError on any failure."""


class LLMError(RuntimeError):
    """Raised on any LLM call failure (network / auth / quota / parse)."""


class LLMQuotaError(LLMError):
    """Raised specifically when the provider returns rate-limit / quota error."""


class LLMResponseParseError(LLMError):
    """Raised when response body cannot be parsed as expected JSON."""
