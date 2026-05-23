"""LLM-specific errors. Never silently swallowed (memory:feedback_no_offline_only)."""
from __future__ import annotations


class LLMError(RuntimeError):
    """Raised on any LLM call failure (network / auth / quota / parse)."""


class LLMQuotaError(LLMError):
    """Raised specifically when the provider returns rate-limit / quota error."""


class LLMResponseParseError(LLMError):
    """Raised when response body cannot be parsed as expected JSON."""
