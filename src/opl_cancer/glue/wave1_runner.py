"""Wave 1 end-to-end orchestrator — plan-load → scaffold → fanout → audit → render.

Spec §4 lifecycle (Wave 1 = team discovery). Harness-split (HARNESS_SPLIT_PRD):
this runner NO LONGER calls an LLM. The host agent (SKILL main thread / dispatched
subagents) is the reasoning executor. The runner is a pure scaffold + validator,
mirroring wave2-4 runners:

1. Intent is host-provided (defaults to ``NEW_GOAL``); the intent_parser LLM call
   is removed (intent classification is now a host-agent decision).
2. The deterministic ``plan.json`` (produced by ``opl-cancer plan``) is loaded —
   or a host-provided ``plan_dict`` is used — instead of an LLM planner call.
3. Pre-fetch integrator results per task (DB/API ``integrate()`` — not an LLM call).
4. ``dispatch_wave`` runs the experts' scaffold/validate ``execute`` concurrently:
   each returns the host-written report artifact if present, else a scaffold.
5. Cross-expert review is dispatched as a host-agent reviewer subagent via
   ``run_reviewer_pairing`` (distinct model + distinct expert, G13) — the
   in-Python reviewer LLM call is removed.
6. Mechanical gates run on every claim (injected via ``gates``) — Python verdicts.
7. ``provenance_hash`` per claim (canonical SHA-256 via ``hash_claim``).
8. ``PatientBriefRenderer`` assembles ``delivery/patient_brief.{html,md}``
   deterministically from the validated artifacts.

Per ADR-2026-04-22 main-thread-only: this runner IS the main thread; Experts
are dispatched once. Recursive ``dispatch_wave`` calls raise.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from opl_cancer.orchestrator.dispatch import ExpertHandler

from opl_cancer.experts.base import Expert
from opl_cancer.glue.case_loader import PatientCaseLoader
from opl_cancer.glue.progress_reporter import ProgressReporter
from opl_cancer.glue.renderer import PatientBriefRenderer
from opl_cancer.glue._post_write import (
    post_write_safety_check as _post_write_safety_check,
)
# NOTE (harness-split): orchestrator.* is the self-improvement engine being
# extracted to a standalone repo. ExpertHandler / dispatch_wave /
# run_reviewer_pairing are imported lazily (in-function at execution time) so
# this runner stays importable when orchestrator/ is absent. ExpertHandler is
# only needed at handler-build time, so the adapter subclass is built lazily via
# ``_expert_handler_adapter_cls()`` below.
from opl_cancer.validators.fakery_sniffer import scan_artifact  # noqa: F401 — back-compat re-export
from opl_cancer.plan.schemas import Plan, Task, WaveAssignment
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal
from opl_cancer.validators.mechanical_gates import Gate, GateStatus


# Per-task-package required integrator-result context keys.
# Each entry: (context_key, integrator_family, fetch_key_source).
# fetch_key_source ∈ {"profile_diagnosis", "ngs_report", "patient_code"} — runner
# uses these to derive the key passed to integrator.cached_fetch().
_TASK_INTEGRATOR_DEPS: dict[str, list[tuple[str, str, str]]] = {
    "molecular_ngs_interpretation": [
        ("oncokb_results", "F4", "ngs_report"),
        ("civic_results", "F4", "ngs_report"),
        ("clinvar_results", "F4", "ngs_report"),
        ("gnomad_results", "F4", "ngs_report"),
        ("pubmed_results", "F1", "ngs_report"),
    ],
    "pathology_interpretation": [
        ("oncokb_results", "F4", "pathology_report"),
        ("civic_results", "F4", "pathology_report"),
        ("pubmed_results", "F1", "pathology_report"),
    ],
    "recist_progression": [
        ("pubmed_results", "F1", "patient_code"),
    ],
    "tcm_oncology": [
        ("pubmed_results", "F1", "patient_code"),
    ],
    "treatment_line_recommendation": [
        ("pubmed_results", "F1", "patient_code"),
        ("nccn_excerpts", "F2", "profile_diagnosis"),
    ],
    "trial_matching": [
        ("ctgov_results", "F3", "profile_diagnosis"),
        ("chictr_results", "F3", "profile_diagnosis"),
        # P0.1 fix: fda_eap.py / nmpa_eap.py declare family="F8" (expanded-access
        # program family), NOT F3. Declaring F3 here meant the EAP integrators
        # were never resolvable by family and EAP context was silently empty.
        ("fda_eap_results", "F8", "profile_diagnosis"),
        ("nmpa_eap_results", "F8", "profile_diagnosis"),
    ],
}


# Extra task-package context keys that the runner derives from PatientCaseLoader
# context but need explicit promotion to template-visible names.
_TASK_EXTRA_CONTEXT: dict[str, list[tuple[str, str]]] = {
    "recist_progression": [
        ("current_report", "imaging_report"),
        ("prior_report", "imaging_report"),
        ("current_regimen", "medication_list"),
    ],
    "tcm_oncology": [
        ("current_regimen", "medication_list"),
        ("symptom_burden", "symptoms"),
        ("organ_function", "labs"),
    ],
    "treatment_line_recommendation": [
        ("cancer_type_stage", "case_text"),
        ("molecular_summary", "ngs_report"),
        ("treatment_history", "treatment_history_doc"),
        ("performance_status", "current_status"),
        ("patient_value", "patient_feedback"),
    ],
    "trial_matching": [
        ("biomarker_summary", "ngs_report"),
        ("treatment_history", "treatment_history_doc"),
        ("location", "current_status"),
    ],
}


_EXPERT_HANDLER_ADAPTER_CLS: type | None = None


def _expert_handler_adapter_cls() -> type:
    """Lazily build the ``ExpertHandler`` adapter subclass.

    ``ExpertHandler`` lives in the orchestrator engine (being extracted to a
    standalone repo). Subclassing it at module-import time would couple this
    runner's importability to orchestrator/. Building the subclass on first use
    (handler-build / execution time) keeps ``import wave1_runner`` clean while
    preserving identical runtime behaviour. The built class is cached.
    """
    global _EXPERT_HANDLER_ADAPTER_CLS
    if _EXPERT_HANDLER_ADAPTER_CLS is not None:
        return _EXPERT_HANDLER_ADAPTER_CLS

    from opl_cancer.orchestrator.dispatch import ExpertHandler

    class _ExpertHandlerAdapter(ExpertHandler):  # type: ignore[misc, valid-type]
        """Adapt an :class:`Expert` to the :class:`ExpertHandler` protocol.

        ``run_task`` calls expert.execute → expert.review and returns both.
        """

        def __init__(self, expert: Expert, task_package: str) -> None:
            self.expert = expert
            self.task_package = task_package

        async def run_task(
            self, task: Task, context: dict[str, Any]
        ) -> dict[str, Any]:
            output = await self.expert.execute(
                task.task_package, plan={}, context=context
            )
            review = await self.expert.review(output, context=context)
            return {"output": output, "review": review}

    _EXPERT_HANDLER_ADAPTER_CLS = _ExpertHandlerAdapter
    return _EXPERT_HANDLER_ADAPTER_CLS


class Wave1Runner:
    def __init__(
        self,
        patient_root: Path,
        out_dir: Path,
        executor_model_id: str,
        reviewer_model_id: str,
        expert_factory: Callable[..., Expert],
        gates: list[Gate],
        *,
        plan_dict: dict[str, Any] | None = None,
        host_artifacts: dict[str, dict[str, Any]] | None = None,
        intent: str = "NEW_GOAL",
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.patient_root = Path(patient_root)
        self.out_dir = Path(out_dir)
        # Harness-split: no LLM clients. model ids are retained as provenance
        # labels + reviewer-pairing inputs (the host agent is the executor).
        self.executor_model_id = executor_model_id
        self.reviewer_model_id = reviewer_model_id
        self.expert_factory = expert_factory
        self.gates = gates
        # Host-provided plan (the deterministic plan.json dict). When None the
        # runner loads <out_dir>/plan.json. Shape: {"experts":[...], "tasks":[...]}.
        self.plan_dict = plan_dict
        # Host-written per-task report artifacts keyed by task_package. Routed
        # into each expert's execute() context as _host_artifacts so the
        # scaffold/validate expert returns the real report instead of a stub.
        self.host_artifacts = host_artifacts or {}
        # Intent is now host-provided (the intent_parser LLM call is removed).
        self.intent = intent
        # v1.5.2: optional plain-language progress reporter. When None,
        # silently no-op (back-compat with v1.4 / v1.5 callers).
        self.reporter = reporter
        # P0.2c: engine-path families that were required but not wired. A
        # non-empty list BLOCKS delivery (no memory substitution).
        self._retrieval_unavailable: list[dict[str, Any]] = []

    # ---- pipeline -------------------------------------------------------

    async def run(self, patient_text: str) -> dict[str, Any]:
        _t0 = time.monotonic()
        # v1.5.2: stage-1 start (lay label "准备 / Getting ready").
        if self.reporter is not None:
            self.reporter.start_stage(
                1,
                action_zh=(
                    "读您的病历 + 找匹配的指南 + 在公开试验库里搜适合您的研究"
                ),
            )
        ctx = PatientCaseLoader(self.patient_root).load()
        # Always promote profile_json (json-encoded profile) for templates
        ctx["profile_json"] = json.dumps(ctx["profile"], ensure_ascii=False)
        # Route host-written report artifacts into the expert execute() context
        # so the scaffold/validate expert returns the real report (keyed by
        # task_package) instead of a stub placeholder.
        ctx["_host_artifacts"] = dict(self.host_artifacts)
        if self.reporter is not None:
            self.reporter.heartbeat(
                1,
                "已经把您的病历读完, 正在判断这次的目标 (新方案 / 复查 / 副作用问题)",
                force=True,
            )

        # 1. Intent — host-provided (intent_parser LLM call removed in harness-split)
        intent = self.intent
        if intent != "NEW_GOAL":
            if self.reporter is not None:
                self.reporter.end_stage(
                    1,
                    summary_zh=(
                        "您的请求不需要团队完整跑一遍, 我可以直接回答"
                    ),
                )
            return {"status": "no_team_run", "intent": intent}
        if self.reporter is not None:
            self.reporter.heartbeat(
                1,
                "已经判定为新方案咨询, 正在让 PI 选哪几位专家上场",
                force=True,
            )

        # 2. Plan
        plan, plan_dict = self._build_plan(patient_text, ctx)
        if self.reporter is not None:
            experts_count = len(plan_dict.get("experts", []))
            self.reporter.heartbeat(
                1,
                f"计划好了, 这次让 {experts_count} 位专家上场, 准备并行开工",
                force=True,
            )

        # 3. Instantiate experts + populate per-task integrator results
        handlers, expert_instances = self._build_handlers(plan_dict["experts"], plan)
        await self._prefetch_integrators(plan, expert_instances, ctx)
        if self.reporter is not None:
            self.reporter.heartbeat(
                1,
                "专家们已经各自查到了背景资料, 现在开始写各自的报告",
                force=True,
            )

        # P0.2c: required live retrieval was unavailable (engine path) → do NOT
        # dispatch experts on missing data, and do NOT ship a brief that looks
        # complete. Render an explicit BLOCKED notice and stop (Evidence
        # Contract: live, never memory — fallback = block, never substitute).
        if self._retrieval_unavailable:
            return self._finalize_blocked_delivery(plan=plan, ctx=ctx)

        # 4. Dispatch wave 1 concurrently
        from opl_cancer.orchestrator.dispatch import dispatch_wave
        outputs = await dispatch_wave(plan, 1, handlers, context=ctx)
        if self.reporter is not None:
            self.reporter.heartbeat(
                1,
                f"{len(outputs)} 位专家都交报告了, 正在做内部核对",
                force=True,
            )

        # 5. Gate enforcement + provenance hash + render
        run_dir = self.out_dir
        prov = ProvenanceJournal(run_dir / "provenance.jsonl")
        rendered_experts, risk_cards = await self._collect_claims(
            plan=plan, outputs=outputs, provenance=prov,
        )
        # Harness-split: a task whose host-agent report was not written back yet
        # comes through as a scaffold placeholder (produced_by="scaffold"). The
        # brief is then INCOMPLETE — surface this honestly rather than ship a
        # brief that silently omits experts (memory:feedback_no_false_completion).
        scaffolded_tasks = [
            task.expert
            for task in plan.tasks
            if outputs.get(task.id, {}).get("output", {}).get("produced_by") == "scaffold"
        ]

        # v2.1 P0-#7: reviewer pairing. For each task that just landed, we
        # persist a per-expert report sidecar AND dispatch a distinct-model
        # + distinct-expert reviewer subagent which writes review.json
        # alongside. Failures escalate (return value will include
        # status="fail" which the SKILL main thread can act on).
        self._persist_per_expert_reports_and_review(
            plan=plan, outputs=outputs, run_dir=run_dir,
        )

        # v2.0.1 (post-review): bridge Wave 2 → renderer so the World-Unknown
        # section actually populates in real runs (was dead template before).
        from opl_cancer.glue.render_bridge import load_world_unknown_candidates

        # P0.2c: a wired-but-not-fully-provisioned engine run BLOCKS delivery.
        # Append explicit Level-3 risk cards so the brief shows the block loudly
        # and never silently fills retrieval gaps from model memory.
        for entry in self._retrieval_unavailable:
            risk_cards.append({
                "level": 3,
                "message": (
                    f"RETRIEVAL UNAVAILABLE — integrator family {entry['family']} "
                    f"not wired for expert {entry['expert']!r} (context "
                    f"{entry['context_key']}). Delivery BLOCKED: OPL refuses to "
                    "substitute live evidence with model memory (SKILL.md "
                    "Evidence Contract)."
                ),
                "requires_ack": True,
            })

        # P0.4: actionable real-world options Wave 1 produced — trial matches,
        # next-line studies, expanded-access routes — promoted to top-level
        # render_ctx so the brief's "Paths you could take / 可以走的路" section
        # (rendered ABOVE the speculative World-Unknown block) shows real,
        # actionable affordances distinct from the speculative ones.
        actionable = self._collect_actionable_options(plan=plan, outputs=outputs)

        renderer = PatientBriefRenderer()
        render_ctx: dict[str, Any] = {
            "patient_code": ctx["patient_code"],
            "run_id": plan.run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "language": ctx.get("profile", {}).get("preferences", {}).get("language", "zh-CN"),
            "sid_summary": "Team analysis complete; see findings below.",
            "risk_cards": risk_cards,
            "experts": rendered_experts,
            "matches": actionable["matches"],
            "studies": actionable["studies"],
            "expanded_access_routes": actionable["expanded_access_routes"],
            "has_actionable_paths": actionable["has_any"],
            "world_unknown_candidates": load_world_unknown_candidates(run_dir),
        }
        if self._retrieval_unavailable:
            render_ctx["delivery_blocked_notice"] = (
                "DELIVERY BLOCKED — required live retrieval was unavailable for: "
                + ", ".join(
                    f"{e['family']} ({e['context_key']})"
                    for e in self._retrieval_unavailable
                )
                + ". OPL will not substitute model memory for live evidence. "
                "Wire the integrator(s) and re-run before treating this brief as valid."
            )
        if scaffolded_tasks:
            render_ctx["run_incomplete_notice"] = (
                "INCOMPLETE RUN — the following experts have not written back a "
                "host-agent report yet: "
                + ", ".join(sorted(set(scaffolded_tasks)))
                + ". Run prompts/experts/expert_task_package.md per scaffold and "
                "re-assemble before treating this brief as complete."
            )
        delivery_dir = run_dir / "delivery"
        renderer.render_html(render_ctx, delivery_dir / "patient_brief.html")
        renderer.render_md(render_ctx, delivery_dir / "patient_brief.md")

        # Emit run_metadata.json for observability tooling (tools/observe.py)
        wall_time = time.monotonic() - _t0
        claims_produced = sum(len(e.get("claims", [])) for e in rendered_experts)
        mechanical_gate_blocks = sum(
            1 for c in risk_cards if c.get("level") == 3 and "BLOCKED" not in str(c.get("message", ""))
        ) + sum(
            1 for e in rendered_experts for c in e.get("claims", [])
            if isinstance(c.get("text"), str) and c["text"].startswith("[BLOCKED")
        )
        triggers_dir = run_dir / "triggers" / plan.run_id
        triggers_dir.mkdir(parents=True, exist_ok=True)
        (triggers_dir / "run_metadata.json").write_text(
            json.dumps({
                "run_id": plan.run_id,
                "token_cost": 0,
                "wall_time_seconds": round(wall_time, 6),
                "claims_produced": claims_produced,
                "claims_withdrawn": 0,
                "reviewer_fail_rate": 0.0,
                "mechanical_gate_blocks": mechanical_gate_blocks,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # v1.5.2: stage-1 end (lay summary, next-stage preview).
        if self.reporter is not None:
            n_experts = len(rendered_experts)
            n_risk_cards = len(risk_cards)
            risk_phrase = (
                f", 其中 {n_risk_cards} 处会附加风险说明"
                if n_risk_cards
                else ""
            )
            self.reporter.end_stage(
                1,
                summary_zh=(
                    f"{n_experts} 位专家的初步资料都齐了{risk_phrase}"
                ),
                next_stage_preview_zh=(
                    "想办法 — 团队会列 10-20 种可能的方案让它们互相比一比"
                ),
            )

        # P0.2c: a not-wired required family blocks delivery — this dominates
        # "incomplete" / "ok" (the brief is not trustworthy without live evidence).
        if self._retrieval_unavailable:
            status = "blocked"
        elif scaffolded_tasks:
            status = "incomplete"
        else:
            status = "ok"
        return {
            "status": status,
            "run_id": plan.run_id,
            "out_dir": str(run_dir),
            "scaffolded_experts": sorted(set(scaffolded_tasks)),
            "retrieval_unavailable": list(self._retrieval_unavailable),
        }

    def _finalize_blocked_delivery(
        self, *, plan: Plan, ctx: dict[str, Any]
    ) -> dict[str, Any]:
        """Render a BLOCKED patient brief (no experts dispatched) → status=blocked.

        P0.2c: invoked when required live retrieval was unavailable in the engine
        path. We never run experts on missing data nor ship a brief that looks
        complete; the brief carries an explicit DELIVERY BLOCKED notice naming
        every unavailable family, and OPL substitutes NO model memory.
        """
        run_dir = self.out_dir
        renderer = PatientBriefRenderer()
        notice = (
            "DELIVERY BLOCKED — required live retrieval was unavailable for: "
            + ", ".join(
                f"{e['family']} ({e['context_key']})"
                for e in self._retrieval_unavailable
            )
            + ". OPL will not substitute model memory for live evidence. "
            "Wire the integrator(s) and re-run before treating this brief as valid."
        )
        render_ctx: dict[str, Any] = {
            "patient_code": ctx["patient_code"],
            "run_id": plan.run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "language": ctx.get("profile", {}).get("preferences", {}).get("language", "zh-CN"),
            "sid_summary": "Delivery blocked — required live retrieval unavailable.",
            "risk_cards": [],
            "experts": [],
            "matches": [],
            "studies": [],
            "expanded_access_routes": [],
            "has_actionable_paths": False,
            "world_unknown_candidates": [],
            "delivery_blocked_notice": notice,
        }
        delivery_dir = run_dir / "delivery"
        renderer.render_html(render_ctx, delivery_dir / "patient_brief.html")
        renderer.render_md(render_ctx, delivery_dir / "patient_brief.md")
        return {
            "status": "blocked",
            "run_id": plan.run_id,
            "out_dir": str(run_dir),
            "scaffolded_experts": [],
            "retrieval_unavailable": list(self._retrieval_unavailable),
        }

    # ---- pipeline stages ------------------------------------------------

    def _load_plan_dict(self) -> dict[str, Any]:
        """Resolve the Wave-1 plan WITHOUT an LLM call (harness-split).

        Resolution order:
        1. ``self.plan_dict`` injected by the caller (host-produced plan).
        2. ``<out_dir>/plan.json`` (the deterministic plan from ``opl-cancer plan``).

        The PI/global planner reasoning that used to run as an LLM call is now
        produced upstream (deterministic comorbid planner / host agent). The
        runner consumes that plan rather than synthesising one.
        """
        if self.plan_dict is not None:
            return dict(self.plan_dict)
        plan_path = self.out_dir / "plan.json"
        if not plan_path.is_file():
            raise FileNotFoundError(
                f"Wave-1 plan not provided and {plan_path} missing. The host agent "
                "must produce a plan (run `opl-cancer plan` or pass plan_dict) — the "
                "in-Python LLM planner was removed in the harness split."
            )
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"{plan_path} is not a JSON object plan")
        return loaded

    def _build_plan(
        self, patient_text: str, ctx: dict[str, Any]
    ) -> tuple[Plan, dict[str, Any]]:
        # Harness-split: load the deterministic plan (host-produced /
        # opl-cancer plan) instead of an LLM planner call. The plan dict may be
        # in the runner shape ({"experts":[...],"tasks":[{id,expert,task_package,
        # sub_goal}]}) or the full Plan-schema shape ({"tasks":[...],"waves":[...]});
        # we normalise to the runner shape.
        raw = self._load_plan_dict()
        plan_dict: dict[str, Any] = {
            "experts": list(raw.get("experts", [])),
            "tasks": [dict(t) for t in raw.get("tasks", [])],
        }
        # Derive experts roster from tasks when not explicitly listed.
        if not plan_dict["experts"]:
            plan_dict["experts"] = sorted(
                {str(t["expert"]) for t in plan_dict["tasks"] if t.get("expert")}
            )
        # De-script (ADR-0040): the plan is composed upstream by the host LLM
        # planner (goal_backward_planner.md) + the deterministic comorbid floor;
        # the runner consumes it as-is. The old keyword intake-router fold is gone.
        # Only Wave-1 tasks (the runner runs a single wave). If the plan carries
        # explicit wave assignments, keep just wave 1; else all tasks are wave 1.
        wave1_ids: list[str] | None = None
        for w in raw.get("waves", []) or []:
            if isinstance(w, dict) and w.get("wave_number") == 1:
                wave1_ids = [str(i) for i in w.get("task_ids", [])]
                break
        tasks = plan_dict["tasks"]
        if wave1_ids is not None:
            wave1_set = set(wave1_ids)
            # Always keep any intake task the router appended.
            tasks = [t for t in tasks if t["id"] in wave1_set or t["id"].startswith("t_intake")]
            plan_dict["tasks"] = tasks
        run_id = str(raw.get("run_id") or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}")
        plan = Plan(
            run_id=run_id,
            patient_code=ctx["patient_code"],
            goal=patient_text,
            waves=[WaveAssignment(
                wave_number=1, task_ids=[t["id"] for t in plan_dict["tasks"]],
            )],
            tasks=[
                Task(
                    id=t["id"], expert=t["expert"], task_package=t["task_package"],
                    sub_goal=t.get("sub_goal", ""), dependencies=[],
                )
                for t in plan_dict["tasks"]
            ],
        )
        return plan, plan_dict

    def _build_handlers(
        self, expert_names: list[str], plan: Plan,
    ) -> tuple[dict[str, ExpertHandler], dict[str, Expert]]:
        expert_instances: dict[str, Expert] = {}
        for name in expert_names:
            # Harness-split: factory no longer receives LLM clients (the host
            # agent is the executor). It receives the expert name + model-id
            # provenance labels only.
            expert_instances[name] = self.expert_factory(
                name,
                self.executor_model_id,
                self.reviewer_model_id,
            )
        adapter_cls = _expert_handler_adapter_cls()
        handlers: dict[str, ExpertHandler] = {}
        # Pick adapter per (expert_name, task_package) — use the first task's pkg.
        for task in plan.tasks:
            handlers[task.expert] = adapter_cls(
                expert_instances[task.expert], task.task_package,
            )
        return handlers, expert_instances

    async def _prefetch_integrators(
        self,
        plan: Plan,
        expert_instances: dict[str, Expert],
        ctx: dict[str, Any],
    ) -> None:
        """Populate ctx with `<context_key>` entries for every task in plan.

        For each task, look up its package in _TASK_INTEGRATOR_DEPS and call
        expert.integrate(family, fetch_key) once. Also promote extra-context
        aliases (e.g. molecular_summary <- ngs_report).

        P0.2 honesty contract — two distinct paths:

        * Claude-Code main-thread / state-reader path: the expert is wired with
          NO integrators (empty map). Retrieval is the HOST agent's job, not the
          runner's. We do NOT fetch and do NOT block — the host fills these keys
          with real live results before writing the report back. (2b)
        * Engine / single-model path: the expert IS wired with integrator
          clients. A required family that is genuinely not in that wired map is a
          retrieval failure. We MUST NOT substitute ``{"results": []}`` (the LLM
          would then fill it from memory — Evidence Contract violation). We
          record an explicit ``retrieval_unavailable`` / ``not_wired`` status and
          register it so the run BLOCKS delivery. (2c)
        """
        from opl_cancer.integrators.base import IntegratorError

        for task in plan.tasks:
            expert = expert_instances[task.expert]
            # Host-dispatch path: retrieval is the host agent's job (NOT the
            # runner's) when EITHER (a) the host already executed this expert and
            # supplied its output via host_artifacts — the evidence is in that
            # report, gated downstream by G35/G36/fakery on the brief — OR (b) the
            # expert is wired with no integrators at all (state-reader). In both
            # cases a missing Python integrator marks PENDING, never blocks. The
            # engine/single-model path (wired expert, required family genuinely
            # absent) is the only case that BLOCKS delivery (Evidence Contract).
            host_supplied = task.task_package in self.host_artifacts
            host_does_retrieval = host_supplied or not getattr(expert, "integrators", None)
            for ctx_key, family, key_source in _TASK_INTEGRATOR_DEPS.get(task.task_package, []):
                if ctx_key in ctx:
                    continue
                key = self._derive_key(key_source, ctx)
                try:
                    result = await expert.integrate(family, key)
                except KeyError:
                    # Family genuinely not wired.
                    if host_does_retrieval:
                        # State-reader path: the HOST agent performs retrieval and
                        # writes live results back before finalizing the report.
                        # We set an explicit PENDING marker (not an empty-results
                        # substitution) so the scaffold template renders AND the
                        # host sees this slot must be filled with live data — never
                        # an empty list the LLM may fill from memory.
                        ctx[ctx_key] = json.dumps(
                            {
                                "status": "pending_host_retrieval",
                                "family": family,
                                "note": (
                                    f"Host agent must run live {family} retrieval "
                                    f"for {ctx_key} and write results back; OPL does "
                                    "NOT substitute model memory."
                                ),
                            },
                            ensure_ascii=False,
                        )
                        continue
                    # Engine path: a wired expert is missing a REQUIRED family.
                    # Fail toward humility — block delivery, never substitute.
                    self._record_retrieval_unavailable(
                        task=task, ctx_key=ctx_key, family=family,
                        reason="not_wired",
                    )
                    result = self._retrieval_unavailable_payload(family, "not_wired")
                except IntegratorError as exc:
                    # Family IS wired but live retrieval failed (network down /
                    # bad key / source error). memory:feedback_no_offline_only —
                    # report + block, NEVER silently fall back to memory.
                    self._record_retrieval_unavailable(
                        task=task, ctx_key=ctx_key, family=family,
                        reason=f"fetch_failed: {exc}",
                    )
                    result = self._retrieval_unavailable_payload(
                        family, f"fetch_failed: {exc}"
                    )
                ctx[ctx_key] = json.dumps(result, ensure_ascii=False)
            for alias, source in _TASK_EXTRA_CONTEXT.get(task.task_package, []):
                if alias in ctx:
                    continue
                ctx[alias] = ctx.get(source, "")

    def _record_retrieval_unavailable(
        self, *, task: Task, ctx_key: str, family: str, reason: str = "not_wired",
    ) -> None:
        """Register an unavailable retrieval so the run blocks delivery (P0.2c).

        Appends to ``self._retrieval_unavailable`` — surfaced as a Level-3
        risk_card + ``status="blocked"`` in :meth:`run`. Never silently dropped.
        ``reason`` ∈ {"not_wired", "fetch_failed: …"}.
        """
        self._retrieval_unavailable.append({
            "task_id": task.id,
            "expert": task.expert,
            "context_key": ctx_key,
            "family": family,
            "reason": reason,
        })

    @staticmethod
    def _retrieval_unavailable_payload(family: str, reason: str) -> dict[str, Any]:
        """Explicit not-available payload routed into the expert context.

        Carries ``blocks_delivery=True`` + ``status="retrieval_unavailable"`` so
        the expert/LLM sees the gap is a HARD block, not an empty result it may
        fill from memory (Evidence Contract: live, never memory).
        """
        return {
            "results": [],
            "status": "retrieval_unavailable",
            "family": family,
            "reason": reason,
            "blocks_delivery": True,
            "note": (
                f"integrator family {family} unavailable ({reason}); live "
                "retrieval unavailable — delivery BLOCKED (no memory substitution)."
            ),
        }

    @staticmethod
    def _collect_actionable_options(
        *, plan: Plan, outputs: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """P0.4: gather REAL actionable options Wave 1 produced.

        Returns ``{matches, studies, expanded_access_routes, has_any}``. These
        are concrete, real-world affordances (open trials, next-line studies,
        compassionate-use / expanded-access routes) — distinct from the
        speculative World-Unknown candidates. The brief surfaces them in a
        dedicated "Paths you could take / 可以走的路" section ABOVE the
        speculative block. Scaffold placeholders contribute nothing.
        """
        matches: list[dict[str, Any]] = []
        studies: list[dict[str, Any]] = []
        eap_routes: list[dict[str, Any]] = []
        for task in plan.tasks:
            exec_out = (outputs.get(task.id) or {}).get("output", {})
            if not isinstance(exec_out, dict):
                continue
            if exec_out.get("produced_by") == "scaffold":
                continue
            for src, dst in (
                ("matches", matches),
                ("studies", studies),
                ("expanded_access_routes", eap_routes),
            ):
                value = exec_out.get(src)
                if isinstance(value, list):
                    dst.extend(item for item in value if isinstance(item, dict))
        return {
            "matches": matches,
            "studies": studies,
            "expanded_access_routes": eap_routes,
            "has_any": bool(matches or studies or eap_routes),
        }

    @staticmethod
    def _derive_key(key_source: str, ctx: dict[str, Any]) -> str:
        if key_source == "profile_diagnosis":
            diag = ctx.get("profile", {}).get("diagnosis", {})
            histology = diag.get("histology", "")
            site = diag.get("primary_site", "")
            return f"{histology} {site}".strip()
        if key_source == "ngs_report":
            return ctx.get("ngs_report", "")[:200] or "ngs"
        if key_source == "pathology_report":
            return ctx.get("pathology_report", "")[:200] or "pathology"
        if key_source == "patient_code":
            return str(ctx.get("patient_code", ""))
        return key_source

    async def _collect_claims(
        self,
        plan: Plan,
        outputs: dict[str, dict[str, Any]],
        provenance: ProvenanceJournal,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rendered_experts: list[dict[str, Any]] = []
        risk_cards: list[dict[str, Any]] = []
        current_patient_code = plan.patient_code
        for task in plan.tasks:
            data = outputs[task.id]
            exec_out: dict[str, Any] = data["output"]
            review: dict[str, Any] = data["review"]
            # Iter 19 (v1.0.11) — cross-patient isolation guard.
            # If expert output carries a `patient_code` field for a different
            # patient, raise immediately to prevent context bleed across cases.
            self._assert_patient_isolation(exec_out, current_patient_code, task.id)
            claims: list[dict[str, Any]] = []
            for raw_claim in self._iter_claim_records(exec_out):
                # P1.6: fail toward humility. A claim with NO declared
                # claim_layer defaults to "speculative" (the most-cautious tier),
                # NOT "exploratory", and emits a risk_card so the missing tier is
                # surfaced rather than silently up-leveled.
                raw_layer = raw_claim.get("claim_layer")
                if raw_layer in ("established", "exploratory", "speculative"):
                    layer = raw_layer
                else:
                    layer = "speculative"
                    risk_cards.append({
                        "level": 2,
                        "message": (
                            f"task {task.id}: a claim was returned with no/invalid "
                            f"claim_layer ({raw_layer!r}); defaulted to "
                            "'speculative' (fail toward humility). Re-label with an "
                            "explicit evidence tier before relying on it."
                        ),
                        "requires_ack": False,
                    })
                claim: dict[str, Any] = {
                    "layer": layer,
                    "text": self._claim_text(raw_claim),
                    "evidence": raw_claim.get("evidence", []),
                    "reviewer_challenges": review.get("challenges", []),
                }
                # Run gates (G1/G2/G3/G9/G11 if provided)
                for gate in self.gates:
                    result = gate.check(claim)
                    if result.status == GateStatus.FAIL and result.block:
                        claim["text"] = f"[BLOCKED by {result.gate}] {result.message}"
                        risk_cards.append({
                            "level": 3,
                            "message": f"{result.gate}: {result.message}",
                            "requires_ack": True,
                        })
                claim["provenance_hash"] = hash_claim({
                    "task_id": task.id,
                    "claim_text": claim["text"],
                })
                provenance.append({
                    "task_id": task.id,
                    "claim": claim["text"],
                    "hash": claim["provenance_hash"],
                })
                claims.append(claim)
            rendered_experts.append({
                "name": task.expert,
                "role": task.task_package,
                "claims": claims,
            })
        return rendered_experts, risk_cards

    def _persist_per_expert_reports_and_review(
        self,
        *,
        plan: Plan,
        outputs: dict[str, dict[str, Any]],
        run_dir: Path,
    ) -> None:
        """v2.1 P0-#7: write per-expert reports + run reviewer pairing.

        Each task gets its own ``tasks/w1_<task_id>/report.md`` sidecar
        (which the artifact-state probe in `cli.wave1` looks for). After
        each write we dispatch a distinct-model + distinct-expert reviewer
        and persist review.json next to it. Reviewer failures are surfaced
        via the review.json status field but do NOT raise here — the
        main thread (SKILL) is the final arbiter of how to react.
        """
        tasks_root = run_dir / "tasks"
        tasks_root.mkdir(parents=True, exist_ok=True)
        for task in plan.tasks:
            data = outputs.get(task.id) or {}
            exec_out = data.get("output", {})
            report_dir = tasks_root / f"w1_{task.id}"
            report_dir.mkdir(parents=True, exist_ok=True)

            # Harness-split: a task with no host-written report yet comes through
            # as a scaffold placeholder. We persist the host-agent execution
            # scaffold (NOT a finished report.md) so the artifact-state probe
            # still sees the task as not-yet-complete and the host agent has the
            # exact prompt + context to run. No fakery sniffer / reviewer pairing
            # runs on a scaffold — those guard finished reports.
            if exec_out.get("produced_by") == "scaffold":
                scaffold = exec_out.get("_scaffold", {})
                (report_dir / "scaffold.json").write_text(
                    json.dumps(scaffold, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                (report_dir / "report.md").write_text(
                    f"# Wave 1 SCAFFOLD — {task.expert} / {task.task_package}\n\n"
                    f"task_id: {task.id}\n\n"
                    "Host-agent report not written back yet. Run the prompt named "
                    "in scaffold.json (`execute_prompt`) with the included system "
                    "prompt + task instructions, then write the JSON report.\n",
                    encoding="utf-8",
                )
                continue

            report_path = report_dir / "report.md"
            report_path.write_text(
                f"# Wave 1 — {task.expert} / {task.task_package}\n\n"
                f"task_id: {task.id}\n\n"
                "## Raw output\n\n"
                f"```json\n{json.dumps(exec_out, ensure_ascii=False, indent=2)}\n```\n",
                encoding="utf-8",
            )
            # v2.1 P1-#9: fakery sniffer on the freshly written report.
            # Hits raise SnifferHalt which propagates out of the wave run.
            _post_write_safety_check(report_path, run_root=run_dir)
            # Reviewer pairing — distinct model + distinct expert (host-agent
            # reviewer subagent dispatched here per G13).
            from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing
            run_reviewer_pairing(
                report_path=report_path,
                primary_expert=task.expert,
                primary_model=self.executor_model_id,
            )

    @staticmethod
    def _iter_claim_records(exec_out: dict[str, Any]) -> list[dict[str, Any]]:
        """Pick the list of claim-shaped records from an Expert's JSON output.

        Different task packages return different top-level shapes:
        - bert.molecular_ngs_interpretation → "variants"
        - rick.trial_matching → "matches"
        - heddy.recist_progression → "target_lesions" wrapped in single claim
        We collect the most common claim-list keys.
        """
        records: list[dict[str, Any]] = []
        for key in ("variants", "matches", "studies", "expanded_access_routes",
                    "differentials", "adjuvant_interventions"):
            value = exec_out.get(key)
            if isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
        return records

    @staticmethod
    def _claim_text(raw_claim: dict[str, Any]) -> str:
        for key in ("summary", "text", "excerpt", "verdict_reason"):
            value = raw_claim.get(key)
            if isinstance(value, str) and value:
                return value
        return json.dumps(raw_claim, ensure_ascii=False)

    @staticmethod
    def _assert_patient_isolation(
        exec_out: dict[str, Any], current_patient_code: str, task_id: str,
    ) -> None:
        """Raise if expert output references a different patient_code.

        Iter 19 cross-patient red-team guard. Scans the top-level
        `patient_code` and any nested-in-claim `patient_code`. Mismatch fails
        loud — silent context bleed is a P0 safety bug.
        """
        top = exec_out.get("patient_code")
        if isinstance(top, str) and top and top != current_patient_code:
            raise CrossPatientContaminationError(
                f"task {task_id}: expert output patient_code={top!r} "
                f"!= current patient_code={current_patient_code!r}"
            )
        for key in ("variants", "matches", "studies", "expanded_access_routes",
                    "differentials", "adjuvant_interventions"):
            records = exec_out.get(key)
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                rec_pc = rec.get("patient_code")
                if isinstance(rec_pc, str) and rec_pc and rec_pc != current_patient_code:
                    raise CrossPatientContaminationError(
                        f"task {task_id}: claim patient_code={rec_pc!r} "
                        f"!= current patient_code={current_patient_code!r}"
                    )


class CrossPatientContaminationError(RuntimeError):
    """Raised when an expert output references a patient_code other than the
    one driving the current run. memory:feedback_no_false_completion — fail
    loud, never silently cross-pollinate."""
