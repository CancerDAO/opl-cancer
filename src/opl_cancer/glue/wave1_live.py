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


# P0.2 fix — integrator registry. The engine/single-model path needs the
# experts to receive REAL integrator clients keyed by family= so that
# ``expert.integrate(family, key)`` performs a live DB/API retrieval rather
# than swallowing a KeyError into an empty result (which the LLM would then
# fill from memory — a SKILL.md Evidence Contract violation:
# "live, never memory / fallback = raise, never substitute").
#
# Concrete integrator classes are listed in deterministic order. Several share
# a family (F1/F3/F4/F8/…); the FIRST class that constructs successfully wins
# that family slot. A class whose constructor raises (e.g. OncoKB without
# ONCOKB_API_KEY) is skipped — the NEXT class for that family is tried, and if
# none construct the family is simply absent from the registry (the runner then
# records an explicit not-wired status that BLOCKS delivery rather than
# substituting empty results).
def _integrator_classes() -> list[type]:
    """Return concrete Integrator subclasses in deterministic registry order.

    Imported lazily so ``import wave1_live`` stays cheap and so an integrator
    module that fails to import (optional heavy dep) does not break wiring.
    """
    from opl_cancer import integrators as _ig

    # Order matters: the first constructible class per family wins. We prefer
    # network-free / key-free clients first so a default registry is usable
    # offline-test-wise, but real runs still hit live endpoints at fetch().
    ordered_names = [
        # F1 literature
        "PubMedIntegrator", "PaperQA2Integrator", "OpenTargetsIntegrator",
        "RetractionDBIntegrator", "UnpaywallIntegrator",
        # F2 guidelines
        "NCCNPageIndexIntegrator",
        # F3 trials
        "ClinicalTrialsGovIntegrator", "ChiCTRIntegrator", "ISRCTNIntegrator",
        "EUCTRIntegrator", "HKCTRIntegrator",
        # F4 variant actionability
        "CIViCIntegrator", "ClinVarIntegrator", "GnomADIntegrator",
        "OncoKBIntegrator",
        # F5 genomic cohorts
        "CBioPortalIntegrator", "GDCIntegrator", "ICGCIntegrator",
        "HartwigIntegrator", "BeatAMLIntegrator",
        # F6 expression archives
        "GEOIntegrator", "ArrayExpressIntegrator", "SRAIntegrator",
        # F7 dependency / cell-line
        "DepMapIntegrator", "CCLEIntegrator",
        # F8 expanded access
        "EMAEAPIntegrator", "FDAEAPIntegrator", "NMPAEAPIntegrator",
        # F9 target evidence
        # (OpenTargets already listed under F1 grouping but declares family F9)
        # F10 drug normalization
        "RxNormIntegrator",
    ]
    classes: list[type] = []
    for name in ordered_names:
        cls = getattr(_ig, name, None)
        if isinstance(cls, type):
            classes.append(cls)
    return classes


def build_integrator_registry(
    *, cache: Any | None = None, strict: bool = False,
) -> dict[str, Any]:
    """Instantiate concrete integrator clients keyed by their ``family=`` attr.

    For each family the first class that constructs successfully is used. A
    class whose constructor raises (missing API key, optional dep) is skipped;
    when ``strict=True`` such failures re-raise instead (used by tests / a
    fully-provisioned engine run that wants every family present).

    Returns ``{family: client}`` — exactly the shape ``LLMBackedExpert``
    expects in its ``integrators`` map, so ``expert.integrate(family, key)``
    performs a real ``cached_fetch``.
    """
    registry: dict[str, Any] = {}
    for cls in _integrator_classes():
        family = getattr(cls, "family", None)
        if not isinstance(family, str) or family in registry:
            continue
        try:
            try:
                client = cls(cache=cache)
            except TypeError:
                # Integrator whose __init__ takes no cache kwarg.
                client = cls()
        except Exception:
            if strict:
                raise
            continue
        registry[family] = client
    return registry


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
    generic expert serves all of them.

    P0.2 fix: when no integrator map is passed the factory now builds the REAL
    integrator registry (``build_integrator_registry``) keyed by family= so
    engine/single-model-path experts perform live ``integrate()`` retrievals
    instead of receiving an empty map. An explicitly-passed ``integrators`` map
    (e.g. ``{}`` for the Claude-Code main-thread state-reader path, or a fakes
    map in tests) is honoured verbatim — pass ``{}`` to preserve the
    host-does-retrieval behaviour.
    """
    shared = build_integrator_registry() if integrators is None else integrators

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
    integrators: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct + run Wave1Runner as a scaffold/validate pass. Returns its result.

    ``run_root`` (``triggers/<run_id>``) IS the runner's out_dir, so scaffolds +
    per-expert reports + the provenance journal land where audit/deliver/attest
    look. ``patient_text`` is read from ``<patient_root>/case_text.md``. When
    ``host_artifacts`` are provided (host-agent reports keyed by task_package) the
    brief assembles fully; otherwise the runner persists scaffolds and returns
    status="incomplete".

    P0.2: ``integrators`` controls retrieval wiring for the engine/single-model
    path. Pass ``{}`` (or rely on the Claude-Code main-thread default) to keep
    the host-does-retrieval state-reader posture; pass a populated map (or omit
    and let ``build_default_expert_factory`` build the real registry) for the
    engine path. When a required family is genuinely not wired the runner records
    an explicit not-wired status that BLOCKS delivery rather than substituting
    empty results.
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
        expert_factory=expert_factory
        or build_default_expert_factory(integrators=integrators),
        gates=gates or [],
        plan_dict=plan_dict,
        host_artifacts=host_artifacts,
        intent=intent,
    )
    return asyncio.run(runner.run(patient_text))


__all__ = [
    "build_default_expert_factory",
    "build_integrator_registry",
    "run_wave1_scaffold",
    "ExpertFactory",
]
