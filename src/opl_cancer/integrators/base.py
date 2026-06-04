"""Integrator abstract base. Spec §2.5 + no-silent-fallback policy.

Iter 15 (v1.0.7) — configurable TTL.
Subclasses may declare `default_ttl_seconds_overrides: dict[str, int]` to
override the class-default `ttl_seconds` for specific keys/sub-families
(e.g. `{"nccn:breast": 7*24*3600}` to cut a faster-changing guideline).
Resolution order at cached_fetch() time:
    1. instance.ttl_seconds_overrides (constructor arg)
    2. cls.default_ttl_seconds_overrides
    3. instance.ttl_seconds (set by __init__; may come from models.yaml)
    4. cls.ttl_seconds

Iter 18 (v1.0.10) — `Integrator.__init__` reads the family default from
`models.yaml.integrator_ttl_seconds[<family_config_key>]` if the subclass
sets `family_config_key`. Models.yaml is lazy-loaded once per process.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

import yaml

from .cache import IntegratorCache


class IntegratorError(RuntimeError):
    """Raised when an integrator cannot serve a request. Never silently swallowed."""


class Integrator(ABC):
    """Abstract base — every concrete integrator inherits.

    family: spec §2.5 F1-F10
    ttl_seconds: default cache TTL (overridable by per-key map or put())
    default_ttl_seconds_overrides: class-level per-key override map
    family_config_key: optional key into models.yaml.integrator_ttl_seconds
        for the family's default TTL (e.g. "nccn", "pubmed").
    """

    family: str
    ttl_seconds: int = 3600
    default_ttl_seconds_overrides: ClassVar[dict[str, int]] = {}
    family_config_key: ClassVar[str | None] = None

    _models_yaml_ttls_cache: ClassVar[dict[str, int] | None] = None

    @classmethod
    def _load_models_yaml_ttls(cls) -> dict[str, int]:
        """Lazy-load `integrator_ttl_seconds` from repo-root models.yaml.

        Returns {} silently if models.yaml is not discoverable (e.g. in an
        installed wheel without source layout). Cached per-process.
        """
        if cls._models_yaml_ttls_cache is not None:
            return cls._models_yaml_ttls_cache
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "models.yaml"
            if candidate.is_file():
                try:
                    data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
                except (yaml.YAMLError, OSError) as exc:
                    raise IntegratorError(
                        f"models.yaml at {candidate} is unreadable or malformed: {exc!r}. "
                        "Refusing to silently fall back to class-default TTLs "
                        "(no-silent-fallback policy / G11 no_silent_fallback). "
                        "Fix the file or remove it from the discovery path."
                    ) from exc
                ttls = data.get("integrator_ttl_seconds", {}) if isinstance(data, dict) else {}
                resolved: dict[str, int] = {
                    str(k): int(v) for k, v in ttls.items() if isinstance(v, (int, float))
                }
                Integrator._models_yaml_ttls_cache = resolved
                return resolved
        Integrator._models_yaml_ttls_cache = {}
        return {}

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        ttl_seconds_overrides: dict[str, int] | None = None,
    ) -> None:
        self.cache = cache
        self.ttl_seconds_overrides: dict[str, int] = dict(ttl_seconds_overrides or {})
        # Iter 18: if subclass declares a config key, prefer models.yaml value
        # over the class-level ttl_seconds default. Instance attribute shadows
        # the class attribute, leaving the class default intact for tests.
        cfg_key = type(self).family_config_key
        if cfg_key is not None:
            ttls = type(self)._load_models_yaml_ttls()
            if cfg_key in ttls:
                self.ttl_seconds = ttls[cfg_key]

    @abstractmethod
    async def fetch(self, key: str) -> dict[str, Any]:
        """Fetch by key (PMID/DOI/NCT ID/etc). MUST raise IntegratorError on failure."""

    def resolve_ttl(self, key: str) -> int:
        """Return the effective TTL (seconds) for `key`.

        Instance overrides beat class overrides; both beat the (instance or
        class) ttl_seconds default.
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
