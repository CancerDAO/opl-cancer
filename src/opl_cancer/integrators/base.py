"""Integrator abstract base. Spec §2.5 + memory:feedback_no_offline_only.

Iter 15 (v1.0.7) — configurable TTL.
Subclasses may declare `default_ttl_seconds_overrides: dict[str, int]` to
override the class-default `ttl_seconds` for specific keys/sub-families
(e.g. `{"nccn:breast": 7*24*3600}` to cut a faster-changing guideline).
Resolution order at cached_fetch() time:
    1. instance.ttl_seconds_overrides (constructor arg)
    2. cls.default_ttl_seconds_overrides
    3. cls.ttl_seconds
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .cache import IntegratorCache


class IntegratorError(RuntimeError):
    """Raised when an integrator cannot serve a request. Never silently swallowed."""


class Integrator(ABC):
    """Abstract base — every concrete integrator inherits.

    family: spec §2.5 F1-F10
    ttl_seconds: default cache TTL (overridable by per-key map or put())
    default_ttl_seconds_overrides: class-level per-key override map
    """

    family: str
    ttl_seconds: int = 3600
    default_ttl_seconds_overrides: ClassVar[dict[str, int]] = {}

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        ttl_seconds_overrides: dict[str, int] | None = None,
    ) -> None:
        self.cache = cache
        self.ttl_seconds_overrides: dict[str, int] = dict(ttl_seconds_overrides or {})

    @abstractmethod
    async def fetch(self, key: str) -> dict[str, Any]:
        """Fetch by key (PMID/DOI/NCT ID/etc). MUST raise IntegratorError on failure."""

    def resolve_ttl(self, key: str) -> int:
        """Return the effective TTL (seconds) for `key`.

        Instance overrides beat class overrides; both beat the class default.
        """
        if key in self.ttl_seconds_overrides:
            return int(self.ttl_seconds_overrides[key])
        if key in self.default_ttl_seconds_overrides:
            return int(self.default_ttl_seconds_overrides[key])
        return int(self.ttl_seconds)

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        """Public entry — checks cache first, then delegates to fetch() + populates cache."""
        if self.cache is not None:
            cached = self.cache.get(family=self.family, key=key)
            if cached is not None:
                return cached
        data = await self.fetch(key)
        if self.cache is not None:
            self.cache.put(
                family=self.family,
                key=key,
                value=data,
                ttl_seconds=self.resolve_ttl(key),
            )
        return data
