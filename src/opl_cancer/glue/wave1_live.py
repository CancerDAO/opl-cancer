"""v2.7.1 ADR-0026 (Fork B) — CLI-self-sufficient Wave-1 execution.

The founder chose to make the CLI able to PRODUCE a compliant run (not merely
verify one) so a run is third-party reproducible without a human-LLM main thread
— when an executor key is present. This revises the 2026-04-22 "CLI holds no LLM
client" posture (see docs/adr/0026-delivery-non-bypassable.md §Fork B).

On Claude Code (no API key for the host model) the agent remains the executor and
`opl-cancer go` orchestrates the dispatch; on a host with an executor key
(MiniMax/Anthropic) `opl run --wave 1` self-executes via this module.

This module is pure wiring around the existing, well-tested ``Wave1Runner`` — it
adds (1) a production expert factory that builds the generic ``LLMBackedExpert``
for ANY of the 20 roster personas (each has prompts/experts/<name>/persona.md),
and (2) ``run_wave1_live`` which constructs + runs the runner. It is injectable
so it can be verified offline with mock LLM clients (no live API needed).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.base import Expert, ExpertProfile
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import Wave1Runner
from opl_cancer.llm.base import LLMClient

ExpertFactory = Callable[[str, LLMClient, LLMClient, str, str], Expert]


class _RosterExpert(LLMBackedExpert):
    """Generic LLM-backed expert for ANY roster persona (Fork B self-exec).

    The concrete subclasses (BertExpert, …) only add a static ``portfolio``
    ClassVar; we instead derive the portfolio from the persona's profile so one
    class serves all 20. Where a persona declares no portfolio (half the roster
    in v2.2), we trust the planner's routing — the global Planner already decided
    which expert owns the task, so ``can_handle`` accepts it rather than blocking
    a legitimately-assigned task.
    """

    def __init__(self, *, profile: ExpertProfile, **kwargs: Any) -> None:
        super().__init__(profile=profile, **kwargs)
        # derive the handled packages from the persona's profile (the concrete
        # subclasses use a static ClassVar; we read the roster instead).
        self._roster_portfolio: tuple[str, ...] = tuple(profile.task_package_portfolio or ())

    def can_handle(self, task_package: str) -> bool:
        if not self._roster_portfolio:
            return True  # no declared restriction → trust the planner's routing
        return task_package in self._roster_portfolio


def build_default_expert_factory(
    integrators: dict[str, Any] | None = None,
) -> ExpertFactory:
    """Return a factory that builds the generic LLMBackedExpert for ANY roster name.

    Every one of the 20 personas has a prompts/experts/<name>/persona.md, so the
    generic LLM-backed expert serves all of them (the concrete subclasses like
    BertExpert add no behaviour beyond identity). A partial/empty integrator map
    is safe: Wave1Runner._prefetch_integrators degrades a missing family to an
    empty result rather than raising.
    """
    shared = integrators or {}

    def factory(
        name: str,
        executor_client: LLMClient,
        reviewer_client: LLMClient,
        executor_model_id: str,
        reviewer_model_id: str,
    ) -> Expert:
        return _RosterExpert(
            profile=get_expert_profile(name),
            executor_client=executor_client,
            reviewer_client=reviewer_client,
            executor_model_id=executor_model_id,
            reviewer_model_id=reviewer_model_id,
            integrators=dict(shared),
        )

    return factory


def run_wave1_live(
    *,
    patient_root: Path,
    run_root: Path,
    intent_client: LLMClient,
    planner_client: LLMClient,
    executor_client: LLMClient,
    reviewer_client: LLMClient,
    executor_model_id: str,
    reviewer_model_id: str,
    expert_factory: ExpertFactory | None = None,
    gates: list[Any] | None = None,
) -> dict[str, Any]:
    """Construct + run Wave1Runner against the patient case. Returns its result.

    ``run_root`` (``triggers/<run_id>``) IS the runner's out_dir, so the
    provenance journal + per-expert reports land where audit/deliver/attest look.
    ``patient_text`` is read from ``<patient_root>/case_text.md``. Injectable
    clients/factory make this verifiable offline with mocks.
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
        intent_client=intent_client,
        planner_client=planner_client,
        executor_client=executor_client,
        reviewer_client=reviewer_client,
        executor_model_id=executor_model_id,
        reviewer_model_id=reviewer_model_id,
        expert_factory=expert_factory or build_default_expert_factory(),
        gates=gates or [],
    )
    return asyncio.run(runner.run(patient_text))


__all__ = ["build_default_expert_factory", "run_wave1_live", "ExpertFactory"]
