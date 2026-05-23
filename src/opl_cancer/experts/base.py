"""Expert abstract base + profile. Spec §2.2."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ExpertProfile(BaseModel):
    name: str
    inspiration: str
    role: str
    persona_summary: str
    task_package_portfolio: list[str] = Field(default_factory=list)
    preferred_integrator_families: list[str] = Field(default_factory=list)


class Expert(ABC):
    """Logical orchestration unit. Main-thread implemented per ADR-2026-04-22.

    Spec §2.2 inner layer: each Expert uses the same 6 task-primitive grammar
    (planner / executor / reviewer / auditor / integrator / feedback). The
    abstract methods below enforce that grammar — subclasses MUST implement
    all six (or explicitly raise NotImplementedError per subclass with rationale).

    Async: per P1-T25 the 5 LLM-touching primitives (plan/execute/review/
    audit/integrate) are async — they wrap network LLM + integrator calls.
    `feedback` stays sync (in-process working-memory write).
    """

    profile: ExpertProfile

    @abstractmethod
    def can_handle(self, task_package: str) -> bool:
        """Return True if this task is in this expert's portfolio."""

    @abstractmethod
    async def plan(self, sub_goal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Spec §2.2 inner grammar — planner primitive.
        Decompose sub_goal into expert-local task plan (not the global Planner)."""

    @abstractmethod
    async def execute(
        self, task_package: str, plan: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Spec §2.2 inner grammar — executor primitive.
        Run the expert's task package on the given plan + context."""

    @abstractmethod
    async def review(
        self, other_output: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Spec §2.2 inner grammar — reviewer primitive (cross-expert peer review).
        Critique another expert's output using DIFFERENT model than the producer."""

    @abstractmethod
    async def audit(self, claim: dict[str, Any]) -> dict[str, Any]:
        """Spec §2.2 inner grammar — auditor primitive (intra-expert pre-audit).
        Catch domain-specific issues before global Henry audit."""

    @abstractmethod
    async def integrate(self, family: str, key: str) -> dict[str, Any]:
        """Spec §2.2 inner grammar — integrator primitive.
        Fetch from this expert's preferred integrator family."""

    @abstractmethod
    def feedback(self, event: dict[str, Any]) -> None:
        """Spec §2.2 inner grammar — feedback primitive.
        Receive patient feedback / new signals; update expert working memory."""
