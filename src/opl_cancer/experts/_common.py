"""Shared Expert base. Wraps P0 Expert ABC as a host-agent SCAFFOLD/VALIDATOR.

Plan refs: P1-T25, harness-split (HARNESS_SPLIT_PRD.md).

v3.x harness-split — the Python expert NO LONGER calls an LLM. The host agent
(the SKILL main thread / a dispatched subagent) is the reasoning executor: it
runs ``prompts/experts/expert_task_package.md`` against the persona + task
template and writes the per-expert report artifact back to disk. This class is
the deterministic scaffold + validator around that hand-off:

- ``scaffold(...)`` composes the exact prompt + input context the host agent
  must run, and the canonical output path it must write to.
- ``execute(...)`` returns the host-written artifact (loaded + structurally
  validated) when present; if it is missing it returns a scaffold-shaped
  placeholder marked ``produced_by="scaffold"`` so the wave runner can persist
  the scaffold and the artifact-state probe / delivery gates can refuse a run
  that never got a real report written back.
- ``review(...)`` no longer makes a cross-model LLM call; cross-expert review is
  now a host-agent reviewer subagent (dispatched via
  ``orchestrator.reviewer_hook.run_reviewer_pairing``). ``review`` here returns a
  deterministic "deferred to host reviewer" verdict so the existing
  execute→review adapter contract still holds without inventing a verdict.

Each concrete expert subclass sets:
- portfolio: tuple[str, ...]            — task package names it handles
- preferred_families: tuple[str, ...]   — integrator families it consults
- persona_version: str                  — recorded in produced_by.prompt_version

Hard rules (per memory + spec) preserved as scaffold semantics:
- No silent degradation: a missing persona prefix is still a HARD FileNotFoundError
  (the scaffold cannot be composed without the v1.5 mandatory infrastructure).
- The Python gates in ``src/opl_cancer/validators/gates/`` keep their decision
  authority; this scaffold only PRODUCES / VALIDATES the artifact shape, it does
  not issue gate verdicts.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, ClassVar

from opl_cancer.prompts_loader import PromptTemplate, find_prompts_root

from .base import Expert, ExpertProfile


class StubMethodWarning(UserWarning):
    """Raised when an Expert primitive that ships as a P1 stub is invoked.

    Spec §2.2 promises 6 task-primitive grammar; through v1.5.5 plan(),
    audit(), feedback() return deterministic constants without an LLM call.
    Callers can `warnings.simplefilter("error", StubMethodWarning)` to fail
    tests that rely on real behaviour from these primitives.
    """


class ExpertArtifactError(RuntimeError):
    """Raised when a host-written expert artifact is malformed.

    Fail-loud per honest-failure policy — a report that does not
    parse / does not carry its provenance _meta is a defect, not something to
    silently paper over with an empty approving result.
    """


# The host-agent prompt that replaces the deleted in-Python LLM ``execute`` call.
EXECUTE_PROMPT_REL = "experts/expert_task_package.md"


class LLMBackedExpert(Expert):
    """Concrete Expert that scaffolds the 6-primitive grammar for a host agent.

    Name kept for back-compat with the 20 concrete subclasses (BertExpert, …)
    and the factory wiring. It no longer calls an LLM in-process — the host
    agent is the executor (harness-split). Subclasses provide:
    - portfolio (class attr): task packages they answer.
    - preferred_families (class attr): integrator families they consume.
    """

    portfolio: ClassVar[tuple[str, ...]] = ()
    preferred_families: ClassVar[tuple[str, ...]] = ()
    persona_version: ClassVar[str] = "v0.1.0"

    # v1.5.2-2: process-wide cache of the canonical persona prefix so we
    # do not re-read the file for every expert invocation.
    _persona_prefix_cache: ClassVar[str | None] = None

    def __init__(
        self,
        profile: ExpertProfile,
        executor_client: Any = None,
        reviewer_client: Any = None,
        executor_model_id: str = "host-agent",
        reviewer_model_id: str = "host-agent-reviewer",
        integrators: dict[str, Any] | None = None,
        *,
        skip_persona_prefix: bool = False,
    ) -> None:
        self.profile = profile
        # Back-compat: the factory / CLI still pass client + model-id positional
        # args. They are no longer used to make network calls (harness-split);
        # the model ids are retained as provenance labels only.
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
        """Read + cache the canonical persona prefix (v1.5 P1-A). All personas
        inherit this block so G7 voice, evidence-tier rubric, patient-anchor
        checklist, traceability footer, and privacy hygiene are enforced
        upstream rather than relying solely on post-hoc gates
        (docs/ANTI_PATTERNS_v1.4.md AP-7)."""
        if cls._persona_prefix_cache is not None:
            return cls._persona_prefix_cache
        path = find_prompts_root() / "experts" / "_shared" / "persona_prefix.md"
        if not path.exists():
            # Hard error: the prefix is v1.5 mandatory infrastructure.
            # Returning an empty string would silently degrade persona
            # quality across the entire skill (no-silent-fallback policy).
            raise FileNotFoundError(
                f"persona prefix missing at {path}. v1.5+ requires this "
                "file. If you intentionally want to skip it (tests only), "
                "pass skip_persona_prefix=True to LLMBackedExpert."
            )
        cls._persona_prefix_cache = path.read_text(encoding="utf-8")
        return cls._persona_prefix_cache

    def _compose_system_prompt(self) -> str:
        """Return the system-prompt body the host agent must use: canonical
        prefix + the expert-specific persona.md. v1.5.2-2.

        Check the prefix first — it is the v1.5 mandatory infrastructure
        and missing it is a louder failure than a missing persona body.
        """
        if not self.skip_persona_prefix:
            prefix = self._load_persona_prefix()
        else:
            prefix = ""
        persona_body = self._persona_path().read_text(encoding="utf-8")
        if not prefix:
            return persona_body
        return f"{prefix}\n\n---\n\n{persona_body}"

    def _task_template(self, task_package: str) -> PromptTemplate:
        path = find_prompts_root() / "tasks" / f"{task_package}.md"
        return PromptTemplate.load(path, version=f"{task_package}@v0.1.0")

    # ---- 6 primitive implementations ---------------------------------------

    def can_handle(self, task_package: str) -> bool:
        return task_package in self.portfolio

    async def plan(self, sub_goal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Expert-local decomposition. STUB — see spec §2.2; P2 will use LLM.

        Returns the static portfolio without LLM-driven sub-goal decomposition.
        Emits StubMethodWarning so callers don't mistake this for real planning.
        """
        warnings.warn(
            f"{self.profile.name}.plan() is a P1 stub (spec §2.2); "
            "returning static portfolio without LLM decomposition",
            StubMethodWarning,
            stacklevel=2,
        )
        return {
            "expert": self.profile.name,
            "sub_goal": sub_goal,
            "task_packages": list(self.portfolio),
        }

    # ---- scaffold + validate (replaces the in-Python LLM executor) ---------

    def scaffold(
        self,
        task_package: str,
        context: dict[str, Any],
        *,
        sub_goal: str = "",
    ) -> dict[str, Any]:
        """Compose the host-agent execution scaffold for one task package.

        Returns the prompt body + system context + rendered task instructions +
        the canonical output schema source the host agent must satisfy. This is
        the deterministic replacement for building an ``LLMRequest`` — the host
        agent reads this and writes back the report artifact.
        """
        if not self.can_handle(task_package):
            raise ValueError(
                f"{self.profile.name!r} cannot handle task_package {task_package!r}; "
                f"portfolio={self.portfolio}"
            )
        persona = self._compose_system_prompt()
        template = self._task_template(task_package)
        task_instructions = template.render(**context)
        return {
            "expert": self.profile.name,
            "task_package": task_package,
            "sub_goal": sub_goal,
            "execute_prompt": EXECUTE_PROMPT_REL,
            "system_prompt": persona,
            "task_instructions": task_instructions,
            "prompt_version": template.version,
            "persona_version": self.persona_version,
            "response_format": "json_object",
        }

    def validate_artifact(
        self, task_package: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate a host-written expert artifact + stamp/repair its _meta.

        The host agent's output JSON is validated for basic structural sanity
        (must be a dict) and the provenance ``_meta`` block is ensured so the
        downstream provenance journal + delivery gates have what they inspect.
        Fail-loud on a non-dict payload.
        """
        if not isinstance(data, dict):
            raise ExpertArtifactError(
                f"{self.profile.name} artifact for {task_package!r} is not a JSON "
                f"object: got {type(data).__name__}"
            )
        meta = data.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta.setdefault("executor_task", task_package)
        meta.setdefault("model", self.executor_model_id)
        meta.setdefault("persona_version", self.persona_version)
        meta.setdefault("produced_by", "host-agent")
        data["_meta"] = meta
        return data

    async def execute(
        self,
        task_package: str,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the host-written report artifact, or a scaffold placeholder.

        Harness-split: this NO LONGER calls an LLM. Resolution order:

        1. If the caller already routed a host-written artifact into
           ``context["_host_artifacts"][task_package]`` (or a per-expert path
           under ``context["_artifact_dir"]``), load + validate + return it.
        2. Otherwise return a scaffold-shaped placeholder
           (``produced_by="scaffold"``) carrying the execution scaffold so the
           wave runner can persist the prompt for the host agent and the
           artifact-state probe refuses to claim completion.
        """
        if not self.can_handle(task_package):
            raise ValueError(
                f"{self.profile.name!r} cannot handle task_package {task_package!r}; "
                f"portfolio={self.portfolio}"
            )
        # 1. host-written artifact injected directly into the context.
        host_artifacts = context.get("_host_artifacts")
        if isinstance(host_artifacts, dict) and task_package in host_artifacts:
            return self.validate_artifact(task_package, host_artifacts[task_package])

        # 1b. host-written artifact on disk under a per-task report dir.
        artifact_dir = context.get("_artifact_dir")
        if artifact_dir:
            candidate = Path(artifact_dir) / f"{self.profile.name}_{task_package}.json"
            if candidate.is_file():
                try:
                    loaded = json.loads(candidate.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise ExpertArtifactError(
                        f"{self.profile.name} artifact {candidate} is not valid JSON: "
                        f"{exc}"
                    ) from exc
                return self.validate_artifact(task_package, loaded)

        # 2. no artifact yet — return the scaffold so the host agent can run it.
        scaffold = self.scaffold(task_package, context, sub_goal=str(plan.get("sub_goal", "")) if isinstance(plan, dict) else "")
        return {
            "produced_by": "scaffold",
            "_scaffold": scaffold,
            "_meta": {
                "executor_task": task_package,
                "model": self.executor_model_id,
                "prompt_version": scaffold["prompt_version"],
                "persona_version": self.persona_version,
                "produced_by": "scaffold",
                "note": (
                    "No host-agent report written back yet. Run "
                    f"{EXECUTE_PROMPT_REL} with the scaffold and write the JSON "
                    "artifact for this task."
                ),
            },
        }

    async def review(
        self,
        other_output: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Cross-expert peer review — deferred to a host-agent reviewer.

        Harness-split: the in-Python cross-model reviewer LLM call is removed.
        The real cross-expert review is dispatched by the wave runner via
        ``orchestrator.reviewer_hook.run_reviewer_pairing`` (a distinct-model +
        distinct-expert host subagent, G13). This method returns a deterministic
        "deferred" verdict so the execute→review adapter contract still holds —
        it does NOT approve or block (no fabricated verdict).
        """
        return {
            "verdict": "deferred_to_host_reviewer",
            "challenges": [],
            "reviewer_model": self.reviewer_model_id,
            "note": (
                "Cross-expert review is dispatched as a host-agent reviewer "
                "subagent (distinct model + distinct expert) by the wave runner; "
                "no in-Python LLM verdict is produced here."
            ),
        }

    async def audit(self, claim: dict[str, Any]) -> dict[str, Any]:
        """Intra-expert pre-audit. STUB — see spec §2.2; P2 will run domain checks.

        Returns a constant 'ok' marker. Emits StubMethodWarning.
        """
        warnings.warn(
            f"{self.profile.name}.audit() is a P1 stub (spec §2.2); "
            "returning 'ok' without domain-specific checks",
            StubMethodWarning,
            stacklevel=2,
        )
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
        """STUB — spec §2.2; P2 hooks event into working memory + planner.

        Currently a no-op; emits StubMethodWarning so callers can detect.
        """
        warnings.warn(
            f"{self.profile.name}.feedback() is a P1 stub (spec §2.2); "
            "event not routed to working memory or planner",
            StubMethodWarning,
            stacklevel=2,
        )
        return None
