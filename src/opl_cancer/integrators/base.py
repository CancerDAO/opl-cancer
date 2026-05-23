"""Integrator abstract base. Spec §2.5 + memory:feedback_no_offline_only."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IntegratorError(RuntimeError):
    """Raised when an integrator cannot serve a request. Never silently swallowed."""


class Integrator(ABC):
    """Abstract base — every concrete integrator inherits."""

    family: str
    ttl_seconds: int

    @abstractmethod
    def fetch(self, key: str) -> dict[str, Any]:
        ...
