"""Shared LLM-backed Expert base. Wraps P0 Expert ABC with concrete LLM calls.

Plan refs: P1-T25.

Each concrete expert subclass sets:
- portfolio: tuple[str, ...]            — task package names it handles
- preferred_families: tuple[str, ...]   — integrator families it consults
- persona_version: str                  — recorded in produced_by.prompt_version

Hard rules (per memory + spec):
- Failure on LLM call MUST raise (no silent degradation to keyword stub)
- Reviewer model MUST != Executor model (G13 enforced by ModelRouter)
- Reviewer is fed a DIFFERENT LLMClient instance than Executor; tests inject
  two distinct fakes to verify split.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.llm.errors import LLMResponseParseError
from opl_cancer.llm.prompts import PromptTemplate, find_prompts_root

from .base import Expert, ExpertProfile


class LLMBackedExpert(Expert):
    """Concrete Expert that wires the 6-primitive grammar through LLMClient calls.

    Subclasses provide:
    - portfolio (class attr): task packages they answer.
    - preferred_families (class attr): integrator families they consume.
    """

    portfolio: ClassVar[tuple[str, ...]] = ()
    preferred_families: ClassVar[tuple[str, ...]] = ()
    persona_version: ClassVar[str] = "v0.1.0"

    def __init__(
        self,
        profile: ExpertProfile,
        executor_client: LLMClient,
        reviewer_client: LLMClient,
        executor_model_id: str,
        reviewer_model_id: str,
        integrators: dict[str, Any] | None = None,
    ) -> None:
        self.profile = profile
        self.executor_client = executor_client
        self.reviewer_client = reviewer_client
        self.executor_model_id = executor_model_id
        self.reviewer_model_id = reviewer_model_id
        self.integrators: dict[str, Any] = integrators or {}

    # ---- internal helpers --------------------------------------------------

    def _persona_path(self) -> Path:
        return find_prompts_root() / "experts" / self.profile.name / "persona.md"

    def _task_template(self, task_package: str) -> PromptTemplate:
        path = find_prompts_root() / "tasks" / f"{task_package}.md"
        return PromptTemplate.load(path, version=f"{task_package}@v0.1.0")

    # ---- 6 primitive implementations ---------------------------------------

    def can_handle(self, task_package: str) -> bool:
        return task_package in self.portfolio

    async def plan(self, sub_goal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Expert-local decomposition. P1: deterministic stub; P2 will use LLM."""
        return {
            "expert": self.profile.name,
            "sub_goal": sub_goal,
            "task_packages": list(self.portfolio),
        }

    async def execute(
        self,
        task_package: str,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.can_handle(task_package):
            raise ValueError(
                f"{self.profile.name!r} cannot handle task_package {task_package!r}; "
                f"portfolio={self.portfolio}"
            )
        persona = self._persona_path().read_text(encoding="utf-8")
        template = self._task_template(task_package)
        prompt_text = template.render(**context)
        req = LLMRequest(
            model=self.executor_model_id,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=8192,
            temperature=0.2,
            system=persona,
            response_format={"type": "json_object"},
        )
        resp = await self.executor_client.complete(req)
        try:
            data: dict[str, Any] = json.loads(resp.content)
        except json.JSONDecodeError as exc:
            raise LLMResponseParseError(
                f"{self.profile.name} executor non-JSON for {task_package!r}: "
                f"{resp.content[:200]!r}"
            ) from exc
        data["_meta"] = {
            "executor_task": task_package,
            "model": self.executor_model_id,
            "prompt_version": template.version,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "persona_version": self.persona_version,
        }
        return data

    async def review(
        self,
        other_output: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Cross-expert peer review using reviewer model (G13: != executor)."""
        prompt = (
            "You are a cross-expert reviewer. Inspect the JSON output below for: "
            "(1) PMID fabrication, (2) quote/claim mismatch, (3) brand vs INN, "
            "(4) self-contradiction, (5) over-confident exploratory→established drift. "
            "Return JSON: {verdict: pass|needs_revision|fail, challenges: [string]}.\n\n"
            f"OUTPUT TO REVIEW:\n{json.dumps(other_output, ensure_ascii=False)}"
        )
        req = LLMRequest(
            model=self.reviewer_model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        resp = await self.reviewer_client.complete(req)
        verdict: dict[str, Any]
        try:
            parsed = json.loads(resp.content)
            verdict = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            verdict = {
                "verdict": "needs_revision",
                "challenges": ["reviewer returned non-JSON response"],
            }
        verdict.setdefault("verdict", "needs_revision")
        verdict.setdefault("challenges", [])
        verdict["reviewer_model"] = self.reviewer_model_id
        return verdict

    async def audit(self, claim: dict[str, Any]) -> dict[str, Any]:
        """Intra-expert pre-audit. P1: marker; P2 will run domain-specific checks."""
        return {
            "intra_expert_audit": "ok",
            "expert": self.profile.name,
        }

    async def integrate(self, family: str, key: str) -> dict[str, Any]:
        if family not in self.integrators:
            raise KeyError(
                f"{self.profile.name!r} has no integrator wired for family {family!r}; "
                f"available={sorted(self.integrators)}"
            )
        result = await self.integrators[family].cached_fetch(key)
        assert isinstance(result, dict)
        return result

    def feedback(self, event: dict[str, Any]) -> None:
        """P1: no-op. P2 hooks event into expert working memory + planner adjustments."""
        return None
