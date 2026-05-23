"""Expert abstract base + profile. Spec §2.2."""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ExpertProfile(BaseModel):
    name: str
    inspiration: str
    role: str
    persona_summary: str
    task_package_portfolio: list[str] = Field(default_factory=list)
    preferred_integrator_families: list[str] = Field(default_factory=list)


class Expert(ABC):
    """Logical orchestration unit. Main-thread implemented per ADR-2026-04-22."""

    profile: ExpertProfile

    @abstractmethod
    def can_handle(self, task_package: str) -> bool:
        ...
