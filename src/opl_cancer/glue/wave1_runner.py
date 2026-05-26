"""Wave 1 end-to-end orchestrator — intent → plan → fanout → audit → render.

Spec §4 lifecycle (Wave 1 = team discovery). Driven entirely by LLM JSON
returns (no hardcoded keyword routing — memory:feedback_default_prompt_over_script).

Pipeline:
1. PI Sid runs ``intent_parser`` LLM call — only ``NEW_GOAL`` proceeds.
2. PI Sid runs planner LLM call → ``Plan(JSON)`` selecting subset of 6 experts.
3. Pre-fetch integrator results per task (per task package's known dependencies +
   expert's ``preferred_families``).
4. ``dispatch_wave`` runs all chosen Experts concurrently via asyncio.gather.
5. Each Expert output → cross-expert reviewer call (different model per G13).
6. Mechanical gates run on every claim (G1/G2/G3/G9/G11 — injected via ``gates``).
7. ``provenance_hash`` per claim (canonical SHA-256 via ``hash_claim``).
8. ``PatientBriefRenderer`` writes ``delivery/patient_brief.{html,md}``.

Per ADR-2026-04-22 main-thread-only: this runner IS the main thread; Experts
are dispatched once. Recursive ``dispatch_wave`` calls raise.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from opl_cancer.experts.base import Expert
from opl_cancer.glue.case_loader import PatientCaseLoader
from opl_cancer.glue.progress_reporter import ProgressReporter
from opl_cancer.glue.renderer import PatientBriefRenderer
from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.llm.prompts import PromptTemplate, find_prompts_root
from opl_cancer.orchestrator.dispatch import ExpertHandler, dispatch_wave
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
        ("fda_eap_results", "F3", "profile_diagnosis"),
        ("nmpa_eap_results", "F3", "profile_diagnosis"),
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


class _ExpertHandlerAdapter(ExpertHandler):
    """Adapt an :class:`Expert` to the :class:`ExpertHandler` protocol.

    ``run_task`` calls expert.execute → expert.review and returns both.
    """

    def __init__(self, expert: Expert, task_package: str) -> None:
        self.expert = expert
        self.task_package = task_package

    async def run_task(self, task: Task, context: dict[str, Any]) -> dict[str, Any]:
        output = await self.expert.execute(task.task_package, plan={}, context=context)
        review = await self.expert.review(output, context=context)
        return {"output": output, "review": review}


class Wave1Runner:
    def __init__(
        self,
        patient_root: Path,
        out_dir: Path,
        intent_client: LLMClient,
        planner_client: LLMClient,
        executor_client: LLMClient,
        reviewer_client: LLMClient,
        executor_model_id: str,
        reviewer_model_id: str,
        expert_factory: Callable[..., Expert],
        gates: list[Gate],
        *,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.patient_root = Path(patient_root)
        self.out_dir = Path(out_dir)
        self.intent_client = intent_client
        self.planner_client = planner_client
        self.executor_client = executor_client
        self.reviewer_client = reviewer_client
        self.executor_model_id = executor_model_id
        self.reviewer_model_id = reviewer_model_id
        self.expert_factory = expert_factory
        self.gates = gates
        # v1.5.2: optional plain-language progress reporter. When None,
        # silently no-op (back-compat with v1.4 / v1.5 callers).
        self.reporter = reporter

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
        if self.reporter is not None:
            self.reporter.heartbeat(
                1,
                "已经把您的病历读完, 正在判断这次的目标 (新方案 / 复查 / 副作用问题)",
                force=True,
            )

        # 1. Intent classification
        intent = await self._classify_intent(patient_text, ctx)
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
        plan, plan_dict = await self._build_plan(patient_text, ctx)
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

        # 4. Dispatch wave 1 concurrently
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

        # v2.0.1 (post-review): bridge Wave 2 → renderer so the World-Unknown
        # section actually populates in real runs (was dead template before).
        from opl_cancer.glue.render_bridge import load_world_unknown_candidates

        renderer = PatientBriefRenderer()
        render_ctx: dict[str, Any] = {
            "patient_code": ctx["patient_code"],
            "run_id": plan.run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "language": ctx.get("profile", {}).get("preferences", {}).get("language", "zh-CN"),
            "sid_summary": "Team analysis complete; see findings below.",
            "risk_cards": risk_cards,
            "experts": rendered_experts,
            "world_unknown_candidates": load_world_unknown_candidates(run_dir),
        }
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

        return {"status": "ok", "run_id": plan.run_id, "out_dir": str(run_dir)}

    # ---- pipeline stages ------------------------------------------------

    async def _classify_intent(self, patient_text: str, ctx: dict[str, Any]) -> str:
        intent_template = PromptTemplate.load(
            find_prompts_root() / "pi" / "intent_parser.md",
            version="intent_parser@v0.1.0",
        )
        intent_prompt = intent_template.render(
            patient_text=patient_text,
            profile_json=ctx["profile_json"],
        )
        intent_resp = await self.intent_client.complete(LLMRequest(
            model=self.executor_model_id,
            messages=[{"role": "user", "content": intent_prompt}],
            max_tokens=512,
            response_format={"type": "json_object"},
        ))
        intent_parsed = json.loads(intent_resp.content)
        intent_raw = intent_parsed.get("intent", "")
        return str(intent_raw)

    async def _build_plan(
        self, patient_text: str, ctx: dict[str, Any]
    ) -> tuple[Plan, dict[str, Any]]:
        # v2.0.1 (post-review): planner now sees the full 20-expert roster
        # including Maya (KG-synergy) + Julius (in-silico medicinal chemist).
        # Hardcoded 6-expert list was the reason Maya / Julius were dead
        # roster entries in v2.0.0-rc1.
        plan_resp = await self.planner_client.complete(LLMRequest(
            model=self.executor_model_id,
            messages=[{"role": "user", "content":
                f"Patient text: {patient_text}\n"
                f"Profile: {ctx['profile_json']}\n"
                "Select 5-12 experts from the v2.0 roster: "
                "[rosa (pathology), bert (NGS/molecular), vince (treating oncology), "
                "rick (trial matching), heddy (imaging), mary (DDI/PGx), aviv (bioinformatics), "
                "tyler (wet-lab design), iain (meta-analysis), ted (radiation), "
                "riad (interventional), jen (palliative), kieren (infection), "
                "mark (irAE endocrine), hong (TCM), frances (expanded access), "
                "dennis (cross-border), steve (nutrition), maya (KG-synergy), "
                "julius (in-silico drug design)].\n"
                "Dispatch heuristics (v2.0.1):\n"
                "- maya MUST be included when patient profile has ≥2 actionable "
                "molecular alterations or asks about target-target synergy.\n"
                "- julius MUST be included when patient profile has an undrugged "
                "actionable target (e.g. MTAP-loss, RB1-loss, undruggable splicing, "
                "or any variant without an FDA-approved drug).\n"
                "- Always include rosa+bert+vince+rick as the minimum spine; "
                "expand based on patient comorbidities + molecular profile.\n"
                "Return strict JSON: {\"experts\": [...], \"tasks\": "
                "[{\"id\":...,\"expert\":...,\"task_package\":...,\"sub_goal\":...}]}"
            }],
            max_tokens=2048,
            response_format={"type": "json_object"},
        ))
        plan_dict: dict[str, Any] = json.loads(plan_resp.content)
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
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
                    sub_goal=t["sub_goal"], dependencies=[],
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
            expert_instances[name] = self.expert_factory(
                name,
                self.executor_client,
                self.reviewer_client,
                self.executor_model_id,
                self.reviewer_model_id,
            )
        handlers: dict[str, ExpertHandler] = {}
        # Pick adapter per (expert_name, task_package) — use the first task's pkg.
        for task in plan.tasks:
            handlers[task.expert] = _ExpertHandlerAdapter(
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
        """
        for task in plan.tasks:
            expert = expert_instances[task.expert]
            for ctx_key, family, key_source in _TASK_INTEGRATOR_DEPS.get(task.task_package, []):
                if ctx_key in ctx:
                    continue
                key = self._derive_key(key_source, ctx)
                try:
                    result = await expert.integrate(family, key)
                except KeyError:
                    result = {"results": [], "note": f"integrator {family} not wired"}
                ctx[ctx_key] = json.dumps(result, ensure_ascii=False)
            for alias, source in _TASK_EXTRA_CONTEXT.get(task.task_package, []):
                if alias in ctx:
                    continue
                ctx[alias] = ctx.get(source, "")

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
                claim: dict[str, Any] = {
                    "layer": raw_claim.get("claim_layer", "exploratory"),
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
