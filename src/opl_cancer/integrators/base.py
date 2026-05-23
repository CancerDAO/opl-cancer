"""Integrator abstract base. Spec §2.5 + memory:feedback_no_offline_only."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .cache import IntegratorCache


class IntegratorError(RuntimeError):
    """Raised when an integrator cannot serve a request. Never silently swallowed."""


class Integrator(ABC):
    """Abstract base — every concrete integrator inherits.

    family: spec §2.5 F1-F10
    ttl_seconds: default per-family cache TTL (overridable by put())
    """

    family: str
    ttl_seconds: int = 3600

    def __init__(self, cache: IntegratorCache | None = None) -> None:
        self.cache = cache

    @abstractmethod
    async def fetch(self, key: str) -> dict[str, Any]:
        """Fetch by key (PMID/DOI/NCT ID/etc). MUST raise IntegratorError on failure."""

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        """Public entry — checks cache first, then delegates to fetch() + populates cache."""
        if self.cache is not None:
            cached = self.cache.get(family=self.family, key=key)
            if cached is not None:
                return cached
        data = await self.fetch(key)
        if self.cache is not None:
            self.cache.put(family=self.family, key=key, value=data, ttl_seconds=self.ttl_seconds)
        return data
