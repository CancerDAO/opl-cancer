"""Wave-1 scaffold runner wiring (harness-split).

Harness-split (HARNESS_SPLIT_PRD): the CLI/runner no longer holds an LLM client
and does not self-execute the reasoning. The host agent (the SKILL main thread
or a dispatched subagent) IS the executor — it runs
``prompts/experts/expert_task_package.md`` against each persona + task template
and writes the per-expert report artifact back. This module is pure wiring around
``Wave1Runner``: it builds the production expert factory (generic scaffold/validate
expert for ANY of the 20 roster personas) and runs the runner as a scaffold pass.

This revises the 2026-04-22/Fork-B "CLI self-sufficient executor" posture — there
is no in-Python LLM dispatch anymore (see docs/adr and HARNESS_SPLIT_PRD).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.base import Expert, ExpertProfile
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import Wave1Runner

# Harness-split factory signature: (name, executor_model_id, reviewer_model_id).
# No LLMClient — the host agent is the executor.
ExpertFactory = Callable[[str, str, str], Expert]


class _RosterExpert(LLMBackedExpert):
    """Generic scaffold/validate expert for ANY roster persona.

    The concrete subclasses (BertExpert, …) only add a static ``portfolio``
    ClassVar; we instead derive the portfolio from the persona's profile so one
    class serves all 20. Where a persona declares no portfolio we trust the
    planner's routing — ``can_handle`` accepts the assigned task rather than
    blocking a legitimately-assigned task.
    """

    def __init__(self, *, profile: ExpertProfile, **kwargs: Any) -> None:
        super().__init__(profile=profile, **kwargs)
        self._roster_portfolio: tuple[str, ...] = tuple(profile.task_package_portfolio or ())

    def can_handle(self, task_package: str) -> bool:
        if not self._roster_portfolio:
            return True  # no declared restriction → trust the planner's routing
        return task_package in self._roster_portfolio


def build_default_expert_factory(
    integrators: dict[str, Any] | None = None,
) -> ExpertFactory:
    """Return a factory that builds the generic scaffold/validate expert for ANY
    roster name.

    Every one of the 20 personas has a prompts/experts/<name>/persona.md, so the
    generic expert serves all of them. A partial/empty integrator map is safe:
    Wave1Runner._prefetch_integrators degrades a missing family to an empty
    result rather than raising.
    """
    shared = integrators or {}

    def factory(
        name: str,
        executor_model_id: str,
        reviewer_model_id: str,
    ) -> Expert:
        return _RosterExpert(
            profile=get_expert_profile(name),
            executor_model_id=executor_model_id,
            reviewer_model_id=reviewer_model_id,
            integrators=dict(shared),
        )

    return factory


def run_wave1_scaffold(
    *,
    patient_root: Path,
    run_root: Path,
    executor_model_id: str = "host-agent",
    reviewer_model_id: str = "host-agent-reviewer",
    plan_dict: dict[str, Any] | None = None,
    host_artifacts: dict[str, dict[str, Any]] | None = None,
    intent: str = "NEW_GOAL",
    expert_factory: ExpertFactory | None = None,
    gates: list[Any] | None = None,
) -> dict[str, Any]:
    """Construct + run Wave1Runner as a scaffold/validate pass. Returns its result.

    ``run_root`` (``triggers/<run_id>``) IS the runner's out_dir, so scaffolds +
    per-expert reports + the provenance journal land where audit/deliver/attest
    look. ``patient_text`` is read from ``<patient_root>/case_text.md``. When
    ``host_artifacts`` are provided (host-agent reports keyed by task_package) the
    brief assembles fully; otherwise the runner persists scaffolds and returns
    status="incomplete".
    """
    run_root = Path(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    case_text_path = Path(patient_root) / "case_text.md"
    if not case_text_path.is_file():
        raise FileNotFoundError(
            f"case_text.md not found under {patient_root} — organize records first "
            "(OPL does not OCR raw uploads; SKILL.md Step 2)."
        )
    patient_text = case_text_path.read_text(encoding="utf-8")

    runner = Wave1Runner(
        patient_root=Path(patient_root),
        out_dir=run_root,
        executor_model_id=executor_model_id,
        reviewer_model_id=reviewer_model_id,
        expert_factory=expert_factory or build_default_expert_factory(),
        gates=gates or [],
        plan_dict=plan_dict,
        host_artifacts=host_artifacts,
        intent=intent,
    )
    return asyncio.run(runner.run(patient_text))


__all__ = ["build_default_expert_factory", "run_wave1_scaffold", "ExpertFactory"]
