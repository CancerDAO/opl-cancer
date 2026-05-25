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

    # v1.5.2-2: process-wide cache of the canonical persona prefix so we
    # do not re-read the file for every expert invocation. Invalidated
    # by restart; the prefix is committed alongside this code so it is
    # stable within a process.
    _persona_prefix_cache: ClassVar[str | None] = None

    def __init__(
        self,
        profile: ExpertProfile,
        executor_client: LLMClient,
        reviewer_client: LLMClient,
        executor_model_id: str,
        reviewer_model_id: str,
        integrators: dict[str, Any] | None = None,
        *,
        skip_persona_prefix: bool = False,
    ) -> None:
        self.profile = profile
        self.executor_client = executor_client
        self.reviewer_client = reviewer_client
        self.executor_model_id = executor_model_id
        self.reviewer_model_id = reviewer_model_id
        self.integrators: dict[str, Any] = integrators or {}
        # v1.5.2-2: escape hatch for tests that want to validate persona
        # behavior in isolation. Production callers leave this False.
        self.skip_persona_prefix = skip_persona_prefix

    # ---- internal helpers --------------------------------------------------

    def _persona_path(self) -> Path:
        return find_prompts_root() / "experts" / self.profile.name / "persona.md"

    def _persona_prefix_path(self) -> Path:
        return find_prompts_root() / "experts" / "_shared" / "persona_prefix.md"

    @classmethod
    def _load_persona_prefix(cls) -> str:
        """Read + cache the canonical persona prefix (v1.5 P1-A). All 18
        personas inherit this block so G7 voice, evidence-tier rubric,
        patient-anchor checklist, traceability footer, and privacy
        hygiene are enforced upstream rather than relying solely on
        post-hoc gates (docs/ANTI_PATTERNS_v1.4.md AP-7)."""
        if cls._persona_prefix_cache is not None:
            return cls._persona_prefix_cache
        path = find_prompts_root() / "experts" / "_shared" / "persona_prefix.md"
        if not path.exists():
            # Hard error: the prefix is v1.5 mandatory infrastructure.
            # Returning an empty string would silently degrade persona
            # quality across the entire skill (memory:feedback_no_offline_only).
            raise FileNotFoundError(
                f"persona prefix missing at {path}. v1.5+ requires this "
                "file. If you intentionally want to skip it (tests only), "
                "pass skip_persona_prefix=True to LLMBackedExpert."
            )
        cls._persona_prefix_cache = path.read_text(encoding="utf-8")
        return cls._persona_prefix_cache

    def _compose_system_prompt(self) -> str:
        """Return the system-prompt body the LLM sees: canonical prefix
        + the expert-specific persona.md. v1.5.2-2.

        Check the prefix first — it is the v1.5 mandatory infrastructure
        and missing it is a louder failure than a missing persona body
        (which usually means a typo in the expert name).
        """
        if not self.skip_persona_prefix:
            prefix = self._load_persona_prefix()
        else:
            prefix = ""
        persona_body = self._persona_path().read_text(encoding="utf-8")
        if not prefix:
            return persona_body
        # Separator: 2 blank lines + a visible boundary so a downstream
        # reader can tell where the shared block ends and the persona
        # begins. Persona body is appended verbatim.
        return f"{prefix}\n\n---\n\n{persona_body}"

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
        # v1.5.2-2: system prompt = canonical persona prefix (v1.5 P1-A,
        # G7 voice + evidence rubric + patient-anchor + traceability +
        # privacy) + this expert's persona.md.
        persona = self._compose_system_prompt()
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
