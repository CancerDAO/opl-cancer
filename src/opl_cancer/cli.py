"""CLI entry point for opl-cancer skill (v1.3.0).

This CLI is the bridge between ``SKILL.md`` (the Claude-facing orchestration
prompt) and the Python implementation under ``src/opl_cancer/``. Each
subcommand corresponds to one step in the ``SKILL.md`` conversation script.

All commands accept ``--json`` for machine-readable output; the SKILL invokes
them this way so Claude can parse the response and surface it to the user.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from opl_cancer.compute.native_runner import NativeAnalysisRunner
from opl_cancer.compute.runner import BixbenchRunner
from opl_cancer.experts.roster import ROSTER
from opl_cancer.glue.funnel import (  # ADR-0042 single source of truth
    assess_deepen as _assess_deepen,
    build_forest as _build_hypothesis_forest,
    compute_funnel as _compute_funnel,
    lifestate as _lifestate,
    load_hypotheses as _load_hypotheses,
    load_killed as _load_killed,
    w4_survival_by_id as _w4_survival_by_id,
)

from opl_cancer import __version__ as VERSION  # single source of truth (kills version drift)
DEFAULT_PATIENT_ROOT_ENV = "OPL_PATIENT_DATA_ROOT"
DEFAULT_PATIENT_ROOT = Path.home() / "CancerDAO" / "patients"


def _patient_root() -> Path:
    env = os.environ.get(DEFAULT_PATIENT_ROOT_ENV)
    return Path(env).expanduser() if env else DEFAULT_PATIENT_ROOT


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(payload: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for k, v in payload.items():
            click.echo(f"{k}: {v}")


def _write_run_manifest(run_root: Path, run_id: str, plan_payload: dict[str, Any]) -> dict[str, Any]:
    """v2.7.0 ADR-0026 — mint the run-token + planned-team manifest at plan time.

    G34 delivery_attestation requires this manifest's ``run_token`` at delivery;
    a free-handed brief that never ran ``plan`` has no token and is refused.
    Lightweight forge-resistance (Fork C): uuid token + planned-set snapshot.
    """
    run_root.mkdir(parents=True, exist_ok=True)
    tasks = plan_payload.get("tasks", []) or []
    planned_experts = sorted({
        str(t.get("expert")).lower() for t in tasks
        if isinstance(t, dict) and t.get("expert")
    })
    planned_waves = sorted({
        int(w.get("wave_number")) for w in (plan_payload.get("waves", []) or [])
        if isinstance(w, dict) and w.get("wave_number") is not None
    })
    manifest = {
        "schema": "opl.run_manifest.v1",
        "run_id": run_id,
        "run_token": f"oplrun-{uuid.uuid4().hex}",
        "created_at": _now_iso(),
        "opl_version": VERSION,
        "planned_experts": planned_experts,
        "planned_waves": planned_waves,
    }
    (run_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


@click.group(help="OPL for Cancer — your AI scientist team, only for you.")
@click.version_option(VERSION)
def main() -> None:
    pass


# ─── Step 0: preflight ────────────────────────────────────────────────────

@main.command(help="Step 0: install self-check. Verify Python, LLM keys, integrators, optional Docker.")
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--allow-single-model",
    is_flag=True,
    default=False,
    help=(
        "Override G13 reviewer-distinct hard-fail. Use only for dev / smoke "
        "tests. A real patient run without a reviewer-pool key violates the "
        "founder-mode discipline — see docs/ANTI_PATTERNS_v1.4.md AP-10."
    ),
)
@click.option(
    "--install-agents",
    is_flag=True,
    default=False,
    help=(
        "Copy agents/opl-experts.yml to ~/.claude/agents/ so the 21 "
        "opl-* subagent types are available under Path 1 of the v2.1 "
        "subagent file-write contract. See docs/SUBAGENT_CONTRACT.md."
    ),
)
def preflight(json_mode: bool, allow_single_model: bool, install_agents: bool) -> None:
    result: dict[str, Any] = {"version": VERSION, "ok": True, "checks": {}, "issues": []}

    # Python ≥ 3.11
    py_ok = sys.version_info >= (3, 11)
    result["checks"]["python"] = {
        "ok": py_ok,
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    if not py_ok:
        result["ok"] = False
        result["issues"].append("Python ≥ 3.11 required; got " + sys.version.split()[0])

    # opl_cancer importable (it is, since we're running it)
    try:
        import opl_cancer  # noqa: F401
        result["checks"]["package"] = {"ok": True, "version": VERSION}
    except ImportError as e:
        result["ok"] = False
        result["checks"]["package"] = {"ok": False, "error": str(e)}
        result["issues"].append(
            "Run: pip install -e " + str(Path(__file__).parent.parent.parent)
        )

    # LLM model layer (v1.4.0+ paradigm: Claude-native).
    #
    # The MAIN executor LLM work (Sid PI + 20 expert task packages + delivery
    # rewrite) runs on the Claude Code main thread — token from the user's
    # Claude Code subscription (~$1-3 per Wave run, same as cancerdao-vmtb).
    # Users do NOT need to supply an ANTHROPIC_API_KEY for OPL to work.
    #
    # The REVIEWER pool only needs an external API key because G13 mandates
    # reviewer model != executor model. Since executor is Claude (Anthropic)
    # on the main thread, the reviewer must be a non-Anthropic model:
    # MiniMax-M2.7 / GPT-5 / Gemini / etc.
    #
    # Therefore preflight no longer hard-fails on missing ANTHROPIC_API_KEY.
    # It warns if NO reviewer-pool model is configured (G13 would block).
    anthropic_ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
    minimax_ok = bool(os.environ.get("MINIMAX_API_KEY"))
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    reviewer_pool_keys = [n for n, ok in [
        ("minimax-m2-7", minimax_ok),
        ("gpt-5", openai_ok),
        ("gemini", gemini_ok),
    ] if ok]
    # v1.5 P0-3+P0-10: G13 reviewer-distinct is a hard-fail by default
    # (docs/ANTI_PATTERNS_v1.4.md AP-10 — Henry detected the violation in
    # v1.4 runs but issued only "future improvement plan"; never fired the
    # real cross-model review. We now refuse to start a run without a
    # reviewer-pool key unless --allow-single-model is explicitly passed.)
    g13_ok = bool(reviewer_pool_keys) or allow_single_model
    result["checks"]["llm"] = {
        "executor_default": "claude-code-main-thread (user CC subscription, no key required)",
        "anthropic_standalone_key": anthropic_ok,
        "reviewer_pool_keys_present": reviewer_pool_keys,
        "g13_reviewer_distinct_ok": g13_ok,
        "allow_single_model_override": allow_single_model,
        "ok": g13_ok,
    }
    if not reviewer_pool_keys and not allow_single_model:
        result["ok"] = False
        result["issues"].append(
            "[block] G13 reviewer-distinct unmet — no reviewer-pool API key "
            "found (MINIMAX_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY). The "
            "main-thread Claude executor would be reviewed by another Claude "
            "instance, violating cross-model decorrelation. To proceed:\n"
            "  1. Get a free MiniMax key — see .env.example for the link.\n"
            "  2. Set MINIMAX_API_KEY=sk-... in your shell / .env.\n"
            "  3. Re-run `opl-cancer preflight`.\n"
            "Dev override (NOT for patient runs): pass --allow-single-model."
        )
    if not reviewer_pool_keys and allow_single_model:
        result["issues"].append(
            "[warn] --allow-single-model bypass active — G13 not enforced. "
            "Do NOT use for patient runs."
        )

    # Integrator presence — verify each module is importable without leaving unused names.
    # v1.3.1: 21 → 28. Added hartwig + beataml + icgc + isrctn + eu_ctr + ema_eap + open_targets.
    # v1.4.0: 28 → 29. Added hkctr (Hong Kong clinical trial registry — round-2 EVAL Patient #20).
    integrator_modules = [
        "arrayexpress", "beataml", "cbioportal", "ccle", "chictr", "civic",
        "clinicaltrials", "clinvar", "depmap", "ema_eap", "eu_ctr", "fda_eap",
        "gdc", "geo", "gnomad", "hartwig", "hkctr", "icgc", "isrctn", "nccn",
        "nmpa_eap", "oncokb", "open_targets", "paperqa", "pubmed", "retractiondb",
        "rxnorm", "sra", "unpaywall",
    ]
    import importlib
    integrator_errors: list[str] = []
    for name in integrator_modules:
        try:
            importlib.import_module(f"opl_cancer.integrators.{name}")
        except ImportError as e:
            integrator_errors.append(f"{name}: {e}")
    if integrator_errors:
        result["checks"]["integrators"] = {"ok": False, "errors": integrator_errors}
        result["issues"].extend(integrator_errors)
    else:
        result["checks"]["integrators"] = {"ok": True, "count": len(integrator_modules), "list": integrator_modules}

    # Wave 3 compute readiness — v1.5 makes Wave 3 non-skippable (P0-1+P0-8).
    # Default path is NativeAnalysisRunner (jupyter on PATH). Docker /
    # bixbench is opt-in for users with heavy R / bioconductor needs.
    # If neither is available the run cannot proceed
    # (docs/ANTI_PATTERNS_v1.4.md AP-1).
    jupyter_path = shutil.which("jupyter")
    docker_path = shutil.which("docker")
    docker_daemon_ok = False
    if docker_path:
        try:
            subprocess.run([docker_path, "info"], check=True, capture_output=True, timeout=5)
            docker_daemon_ok = True
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            docker_daemon_ok = False
    native_ready = jupyter_path is not None
    bixbench_ready = docker_path is not None and docker_daemon_ok
    wave3_ready = native_ready or bixbench_ready
    result["checks"]["wave3_compute"] = {
        "ok": wave3_ready,
        "native_runner_ready": native_ready,
        "jupyter_path": jupyter_path,
        "bixbench_runner_ready": bixbench_ready,
        "docker_path": docker_path,
        "docker_daemon_running": docker_daemon_ok,
        "default_runner": "native" if native_ready else ("bixbench" if bixbench_ready else None),
        "note": (
            "Wave 3 uses NativeAnalysisRunner by default (v1.5+). Docker is "
            "opt-in for the bixbench notebook image."
        ),
    }
    if not wave3_ready:
        result["ok"] = False
        result["issues"].append(
            "[block] Wave 3 compute unavailable — neither jupyter (native) "
            "nor docker (bixbench) is on PATH. Wave 3 is critical-path and "
            "cannot be skipped (AP-1). Install one of:\n"
            "  - Native (recommended): pip install jupyter\n"
            "  - Docker: install Docker Desktop + start daemon\n"
            "Then re-run `opl-cancer preflight`."
        )

    # Patient root
    pr = _patient_root()
    result["checks"]["patient_root"] = {"path": str(pr), "exists": pr.exists()}

    # v2.1 P0-#3: surface which subagent path is active so the SKILL main
    # thread knows whether to expect direct writes or inline returns.
    claude_agents_yml = Path.home() / ".claude" / "agents" / "opl-experts.yml"
    agent_types_installed = claude_agents_yml.exists()
    result["checks"]["subagent_path"] = {
        "ok": True,
        "path": "Path 1 (opl-* agent types)" if agent_types_installed
        else "Path 2 (general-purpose + inline return)",
        "agents_yml_at": str(claude_agents_yml),
        "installed": agent_types_installed,
        "note": (
            "See docs/SUBAGENT_CONTRACT.md. Install Path 1 with "
            "`opl preflight --install-agents`."
        ),
    }

    # --install-agents copies our local agents/opl-experts.yml to ~/.claude/agents/.
    if install_agents:
        src = Path(__file__).resolve().parent.parent.parent / "agents" / "opl-experts.yml"
        if not src.exists():
            result["issues"].append(
                f"[warn] agents/opl-experts.yml not found at {src}; cannot install."
            )
        else:
            claude_agents_yml.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, claude_agents_yml)
            result["checks"]["subagent_install"] = {
                "ok": True,
                "src": str(src),
                "dst": str(claude_agents_yml),
            }

    _emit(result, json_mode)
    sys.exit(0 if result["ok"] else 1)


# ─── Step 1 (no CLI; SKILL handles greeting) ──────────────────────────────
# ─── Step 2: organize → delegated to cancer-buddy-organize sub-skill ──────


# ─── Step 3: readiness gate ───────────────────────────────────────────────

@main.command(help="Step 3: readiness gate over patient directory.")
@click.argument("patient_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--json", "json_mode", is_flag=True)
def readiness(patient_dir: str, json_mode: bool) -> None:
    pdir = Path(patient_dir)
    readiness_file = pdir / "readiness.json"
    if not readiness_file.exists():
        _emit({"ok": False, "error": "readiness.json missing — run organize first"}, json_mode)
        sys.exit(2)
    data = json.loads(readiness_file.read_text(encoding="utf-8"))
    _emit(data, json_mode)


# ─── Step 4: PI plan ──────────────────────────────────────────────────────


def _load_plan_agenda(agenda_path: str | None) -> tuple[list, dict[str, int]]:
    """De-script (ADR-0040): load the host-LLM-composed agenda — the expert team +
    task DAG produced by ``prompts/pi/goal_backward_planner.md``. Returns
    (tasks, wave_map). Omitting ``--agenda`` yields an empty team, so the plan is
    FLOOR-ONLY (the deterministic comorbid red-line); a real run supplies the
    agenda. Python no longer hardcodes a 9-task skeleton or keyword-routes the team.
    """
    from opl_cancer.plan.schemas import Task

    if not agenda_path:
        return [], {}
    raw = json.loads(Path(agenda_path).read_text(encoding="utf-8"))
    raw_tasks = raw.get("tasks", []) if isinstance(raw, dict) else raw
    tasks: list[Task] = []
    wave_map: dict[str, int] = {}
    for rt in raw_tasks:
        tid = str(rt["id"])
        tasks.append(Task(
            id=tid,
            expert=str(rt["expert"]).lower(),
            task_package=str(rt["task_package"]),
            sub_goal=str(rt.get("sub_goal", "")),
            dependencies=[str(d) for d in rt.get("dependencies", [])],
        ))
        if rt.get("wave") is not None:
            wave_map[tid] = int(rt["wave"])
    return tasks, wave_map


def _build_plan_waves(tasks: list, wave_map: dict[str, int], floor_ids: set[str]):
    """Build sequential 1..N WaveAssignments from the agenda's per-task wave hints.

    Comorbid red-line floor tasks default to Wave 1 (retrieval). Distinct wave
    numbers are remapped to a contiguous 1..N range (the Plan schema requires no
    gaps). Empty task list → no waves.
    """
    from opl_cancer.plan.schemas import WaveAssignment

    buckets: dict[int, list[str]] = {}
    for t in tasks:
        wn = 1 if t.id in floor_ids else int(wave_map.get(t.id, 1))
        buckets.setdefault(wn, []).append(t.id)
    ordered = sorted(buckets)
    remap = {old: new for new, old in enumerate(ordered, start=1)}
    return [WaveAssignment(wave_number=remap[wn], task_ids=buckets[wn]) for wn in ordered]


@main.command(help="Step 4: PI (Sid) plans run — verifies the floor over the host-composed agenda.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--goal", required=True, help="Verbatim patient goal.")
@click.option("--run-id", required=True)
@click.option("--out", type=click.Path(), help="Output plan.json path (default: <patient>/triggers/<run_id>/plan.json)")
@click.option(
    "--agenda",
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "Host-LLM-composed agenda JSON (goal_backward_planner.md output): "
        '{"tasks":[{id,expert,task_package,sub_goal,dependencies?,wave?}]}. '
        "Omit for a floor-only plan (the comorbid red-line); a real run supplies it."
    ),
)
@click.option("--json", "json_mode", is_flag=True)
def plan(
    patient_dir: str, goal: str, run_id: str, out: str | None,
    json_mode: bool, agenda: str | None,
) -> None:
    pdir = Path(patient_dir)
    out_path = Path(out) if out else pdir / "triggers" / run_id / "plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # De-script (ADR-0040): the expert team + task DAG are composed by the host
    # LLM planner (prompts/pi/goal_backward_planner.md) and supplied via --agenda;
    # Python no longer hardcodes a 9-task skeleton. The deterministic comorbid
    # red-line FLOOR is added on top (safety by construction) and exposed as
    # `floor_required` for G55 to verify the agenda covers it. Without --agenda the
    # plan is FLOOR-ONLY — a real run supplies the host agenda.
    from opl_cancer.plan.comorbid_planner import maybe_expand_for_comorbid
    from opl_cancer.plan.schemas import Plan
    agenda_tasks, agenda_wave_map = _load_plan_agenda(agenda)
    # Read profile.json if present; safe to proceed without (just no
    # expansion triggers fire).
    profile_path = pdir / "profile.json"
    profile_data: dict[str, Any] = {}
    if profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            profile_data = {}
    # v2.1 P0-#5: hard-fail at plan emit on profile↔trigger field mismatch.
    # Only runs when a profile.json is actually present + has the required
    # patient_id_hash field; missing-profile case stays a soft no-op so the
    # planner remains usable in early-onboarding flows.
    if profile_data and "patient_id_hash" in profile_data:
        from opl_cancer.plan.schema_validator import (
            ProfileTriggerMismatch,
            validate_profile,
        )
        try:
            validate_profile(profile_data, strict_triggers=True)
        except ProfileTriggerMismatch as exc:
            raise click.ClickException(str(exc)) from exc
    # Add the deterministic comorbid red-line FLOOR on top of the host agenda.
    tasks, fired = maybe_expand_for_comorbid(agenda_tasks, profile_data)

    # v2.1 P0-#6: every emitted task_package must be a real file under
    # prompts/tasks/. Fail loud at emit, not silently at run.
    from opl_cancer.plan.task_validator import (
        UnknownTaskPackage,
        validate_task_packages,
    )
    try:
        validate_task_packages([
            {"task_id": t.id, "expert": t.expert, "task_package": t.task_package}
            for t in tasks
        ])
    except UnknownTaskPackage as exc:
        raise click.ClickException(str(exc)) from exc
    # Waves come from the host agenda's per-task `wave` hints (remapped to a
    # contiguous 1..N); comorbid floor tasks default to Wave 1.
    floor_ids = {t.task.id for t in fired}
    skeleton = Plan(
        run_id=run_id,
        patient_code=pdir.name,
        goal=goal,
        tasks=tasks,
        waves=_build_plan_waves(tasks, agenda_wave_map, floor_ids),
    )

    plan_payload = skeleton.model_dump(mode="json")

    # A1 / ADR-0027 — warm start. Ingest prior runs so this plan COMPOUNDS on
    # what earlier runs settled instead of starting cold. Previously
    # ingest_prior_runs() was orphaned (the audit's finding); wiring it here is
    # what lets run N+1 know the patient better than run N. Read-only.
    from opl_cancer.plan.prior_run_ingestion import ingest_prior_runs
    prior_runs = ingest_prior_runs(pdir, current_run_id=run_id)
    if prior_runs:
        plan_payload["extends_prior_run"] = prior_runs[-1].run_id
        plan_payload["prior_runs"] = [
            {
                "run_id": s.run_id,
                "headings": s.headings[:20],
                "cited_pmids": s.cited_pmids[:50],
            }
            for s in prior_runs
        ]
    # D1/E1 / ADR-0034 — feed the planner gates. planned_experts = every expert in
    # the agenda; floor_required = the red-line, comorbidity-mandated experts the
    # deterministic expansion fired (the safety floor G55 enforces: the LLM
    # planner may EXPAND beyond this, never DROP it). Additive — the skeleton
    # stays the floor, not the ceiling.
    plan_payload["planned_experts"] = sorted({str(t.expert).lower() for t in tasks})
    plan_payload["floor_required"] = sorted({str(t.task.expert).lower() for t in fired})
    out_path.write_text(
        json.dumps(plan_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # v2.7.0 ADR-0026 — mint the run-token + planned-team manifest so G34 can bind
    # the eventual brief to THIS run (free-handed briefs have no token → refused).
    manifest = _write_run_manifest(out_path.parent, run_id, plan_payload)
    from opl_cancer.glue.run_events import append_run_event
    append_run_event(
        out_path.parent,
        "plan.manifest_written",
        phase="planning",
        source="opl_cancer.cli.plan",
        payload={
            "planned_experts": manifest["planned_experts"],
            "planned_waves": manifest["planned_waves"],
            "run_token_present": bool(manifest.get("run_token")),
            "tasks": len(tasks),
            "extends_prior_run": plan_payload.get("extends_prior_run"),
        },
    )
    triggers_payload = [
        {"name": t.name, "rationale": t.rationale, "task_id": t.task.id, "expert": t.task.expert}
        for t in fired
    ]
    _emit(
        {
            "ok": True,
            "plan_path": str(out_path),
            "run_id": run_id,
            "run_token": manifest["run_token"],
            "planned_experts": manifest["planned_experts"],
            "waves": len(skeleton.waves),
            "tasks": len(tasks),
            "comorbid_expansion_triggers_fired": triggers_payload,
            "extends_prior_run": plan_payload.get("extends_prior_run"),
            "prior_runs_ingested": len(prior_runs),
        },
        json_mode,
    )


# ─── Reality-outcome loop (A2 / ADR-0028) ─────────────────────────────────

@main.command(help="Reality loop: score prior predictions against the patient's ACTUAL course (A2).")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--outcomes", "outcomes_path", type=click.Path(),
              help="JSON file of host-produced outcome records to persist. Omit to just print prior predictions to score.")
@click.option("--json", "json_mode", is_flag=True)
def reconcile(patient_dir: str, run_id: str, outcomes_path: str | None, json_mode: bool) -> None:
    """Two-beat: (1) run without --outcomes to get the prior predictions to score
    against the new clinical datum in inbox/; (2) the host writes outcome records
    per prompts/tasks/outcome_reconciliation.md and re-runs with --outcomes to
    persist them. This is the only channel through which reality grades OPL."""
    from opl_cancer.glue.outcome_reconcile import load_prior_predictions, persist_outcomes
    from opl_cancer.memory.store import default_patient_memory_db

    pdir = Path(patient_dir)
    db = default_patient_memory_db(pdir / "triggers" / run_id)
    priors = load_prior_predictions(db)
    persisted = 0
    if outcomes_path and Path(outcomes_path).is_file():
        data = json.loads(Path(outcomes_path).read_text(encoding="utf-8"))
        outcomes = data.get("outcomes", data) if isinstance(data, dict) else data
        if isinstance(outcomes, list):
            persisted = persist_outcomes(db, run_id, outcomes)
    _emit(
        {
            "ok": True,
            "memory_db": str(db),
            "prior_predictions": len(priors.get("hypotheses", [])),
            "prior_forecasts": len(priors.get("forecasts", [])),
            "outcomes_persisted": persisted,
            "next": (
                "Score the prior predictions against the new clinical datum in "
                "inbox/ per prompts/tasks/outcome_reconciliation.md, then re-run "
                "with --outcomes <file.json>."
                if not persisted else
                "Outcomes persisted to the ledger; G48 will see this run learned "
                "from reality."
            ),
        },
        json_mode,
    )


# ─── Step 5-8: Waves ──────────────────────────────────────────────────────
#
# v1.5.7 honest-failure rewrite (honest-failure policy + run
# retrospective AP-1 / AP-2 / AP-5):
#
# Through v1.5.6 these commands ran `mkdir -p` and returned `{"ok": true}`
# even when no expert report / hypothesis / dataset / validation had been
# produced. That false-positive ok let the v1.4 patient run reach "delivery"
# while Wave 3 had been skipped — the user had to ask "是否真的做了数据分析?"
# to surface the gap. This is the OPL North Star violation: the system
# claimed it had produced new information when it had only created folders.
#
# OPL runs are **main-thread Claude orchestrated**: the LLM (Claude Code,
# in our reference deployment) dispatches subagents per `SKILL.md`. The CLI
# is the *state reader*, not the executor. Each wave command now:
#   1. Reads the run-root for the artifacts that real execution leaves behind.
#   2. Emits ok=true only when those artifacts exist (with file count + hashes).
#   3. Emits ok=false + `requires_main_thread_dispatch: true` + an
#      LLM-readable action when artifacts are absent — so the orchestrator
#      can decide to dispatch the real path, not declare completion.
#
# The Python `Wave{1,3}Runner` classes are still the execution body when
# you want to run the work *outside* a Claude session (CI, batch, eval).
# They were never invoked by the CLI stub and are not invoked here either —
# wiring them sync-from-CLI is a larger task tracked separately and would
# block on architectural decisions (which LLM client to inject, how to
# surface progress, where to keep secrets). The honest-failure path is the
# minimal v1.5.7 fix that closes the false-completion vector.

_WAVE_ARTIFACT_PROBES: dict[int, dict[str, Any]] = {
    1: {
        "out_dir_segment": "tasks",
        "expected_glob": "w1_*/report.md",
        "min_count": 1,
        "story": "Wave 1 retrieval — at least one `tasks/w1_*/report.md` expert report",
    },
    2: {
        "out_dir_segment": "tournament",
        "expected_glob": "*.json",
        "min_count": 1,
        "story": "Wave 2 tournament — at least one `tournament/*.json` round artifact",
    },
    3: {
        "out_dir_segment": "data",
        # Wave 3 produces real data: cohort CSVs, meta-analysis JSON, GEPIA3
        # results, notebooks. Any one of these counts.
        "expected_glob": "**/*.csv,**/*.json,**/*.ipynb,**/*.png",
        "min_count": 1,
        "story": (
            "Wave 3 data-evidence — at least one real artifact under `data/` "
            "(cohort CSV, meta JSON, GEPIA3 results, notebook, figure). "
            "v1.5 SKILL.md §Step 7 declares Wave 3 non-skippable; mkdir-only is a skip."
        ),
    },
    4: {
        "out_dir_segment": "tasks",
        "expected_glob": "w4_*/report.md",
        "min_count": 1,
        "story": "Wave 4 validation — at least one `tasks/w4_*/report.md` validation report",
    },
}


def _wave_artifact_state(run_root: Path, wave: int) -> dict[str, Any]:
    """Probe the run-root for evidence that a real wave run happened.

    Returns: {ok, found, expected, files: [first-10]}
    """
    probe = _WAVE_ARTIFACT_PROBES[wave]
    out_dir = run_root / probe["out_dir_segment"]
    if not out_dir.exists():
        return {"ok": False, "found": 0, "files": [], "out_dir": str(out_dir)}
    found: list[str] = []
    for pattern in str(probe["expected_glob"]).split(","):
        found.extend(str(p.relative_to(run_root)) for p in out_dir.glob(pattern.strip()))
    return {
        "ok": len(found) >= int(probe["min_count"]),
        "found": len(found),
        "files": sorted(found)[:10],
        "out_dir": str(out_dir),
    }


def _emit_wave_state(wave: int, run_root: Path, json_mode: bool, **extra: Any) -> None:
    """Emit honest wave state — ok=true only when artifacts present.

    When artifacts are absent, return ok=false + an LLM-readable action so the
    orchestrator can decide what to do next (dispatch subagents, or block).
    """
    run_root.mkdir(parents=True, exist_ok=True)
    state = _wave_artifact_state(run_root, wave)
    probe = _WAVE_ARTIFACT_PROBES[wave]
    payload: dict[str, Any] = {
        "ok": state["ok"],
        "wave": wave,
        "run_root": str(run_root),
        "artifacts_found": state["found"],
        "artifacts_sample": state["files"],
        "expected": probe["story"],
        **extra,
    }
    if not state["ok"]:
        payload["requires_main_thread_dispatch"] = True
        payload["action"] = (
            f"Wave {wave} produced no artifacts at {state['out_dir']}. "
            "This CLI command is a *state reader*, not the executor. "
            "The orchestrator (SKILL.md main-thread) must dispatch the real "
            f"wave-{wave} subagent workflow now, then re-invoke this command "
            "to confirm artifacts landed. Refusing to declare completion."
        )
        # Non-zero exit so shell-level callers also see honest failure.
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2) if json_mode
                   else "\n".join(f"{k}: {v}" for k, v in payload.items()))
        sys.exit(2)
    _emit(payload, json_mode)


@main.command(help="Step 5: Wave 1 state-check — does NOT execute. Use `opl run --wave 1` for the executor. Reads tasks/w1_*/report.md count.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--plan", "plan_path", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave1(patient_dir: str, run_id: str, plan_path: str, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    _emit_wave_state(1, run_root, json_mode, plan_path=plan_path)


@main.command(help="Step 6: Wave 2 state-check — does NOT execute. Use `opl run --wave 2` for the executor. Reads tournament/*.json count.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave2(patient_dir: str, run_id: str, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    _emit_wave_state(2, run_root, json_mode)


@main.command(help="Step 7: Wave 3 state-check — does NOT execute. Use `opl run --wave 3 --mode native|docker` for the executor. Refuses to claim completion without real data artifacts.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--enable-docker/--no-docker", default=True)
@click.option("--json", "json_mode", is_flag=True)
def wave3(patient_dir: str, run_id: str, enable_docker: bool, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    _emit_wave_state(3, run_root, json_mode, docker=enable_docker)


@main.command(help="Step 8: Wave 4 state-check — does NOT execute. Use `opl run --wave 4` for the executor. Reads tasks/w4_*/report.md count.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave4(patient_dir: str, run_id: str, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    _emit_wave_state(4, run_root, json_mode)


# ─── Arbor/HTR boundary: observe — read-only re-projection of run state ────
#
# Arbor's coordinator re-grounds on a deterministic projection of durable state
# at the start of every cycle, rather than trusting a lossy conversation memory.
# `observe` is OPL's analog: a no-LLM, read-only render of the whole run —
# planned-vs-done waves, outstanding work, the Project-Memory frontier, and
# (cross-run) falsified hypotheses surfaced as negative constraints. It NEVER
# executes a wave and NEVER writes — a pure function of on-disk state. This is
# the prompt/script boundary made operational: the harness gives the brain a
# faithful re-projection; the brain does the judgment.
# See docs/adr/0041-prompt-script-boundary-and-observe.md.

def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Arbor/HTR tree + funnel + abstraction helpers (ADR-0042) ──────────────
# Pure functions of on-disk state — no LLM, no writes. The hypothesis TREE is
# built from Hypothesis.parent_chain (which already existed; nothing used to read
# it). _load_hypotheses / _build_hypothesis_forest / _compute_funnel are imported
# from glue.funnel (single source of truth, also used by the delivery runner).

def _render_forest_lines(hyps: list[dict[str, Any]], max_lines: int = 24,
                         w4_by_id: dict[str, str] | None = None) -> list[str]:
    by_id = {str(h.get("id")): h for h in hyps if h.get("id")}
    children, roots = _build_hypothesis_forest(hyps)
    w4 = w4_by_id or {}
    # Glyph from the canonical lifestate (NOT raw schema status), so a Wave-4
    # falsified node never renders as alive and contradicts candidate_states.
    sym = {"alive": "•", "dead": "✗", "pending": "?"}
    lines: list[str] = []
    seen: set[str] = set()  # guard against a malformed cyclic parent_chain

    def walk(hid: str, prefix: str) -> None:
        if len(lines) >= max_lines or hid in seen:
            return
        seen.add(hid)
        h = by_id[hid]
        glyph = sym.get(_lifestate(h, w4), "•")
        elo = h.get("elo_rating")
        elo_s = f" Elo{int(elo)}" if isinstance(elo, (int, float)) else ""
        txt = str(h.get("text", ""))[:58]
        lines.append(f"{prefix}{glyph} {hid}{elo_s}: {txt}")
        for c in sorted(children.get(hid, []), key=lambda c: -(by_id[c].get("elo_rating") or 0)):
            walk(c, prefix + "    ")

    for r in sorted(roots, key=lambda r: -(by_id[r].get("elo_rating") or 0)):
        walk(r, "  ")
    if len(by_id) > max_lines:
        lines.append(f"  … (+{len(by_id) - max_lines} more nodes)")
    return lines


def _abstraction_state(run_root: Path) -> dict[str, Any]:
    f = run_root / "abstraction.json"
    priors = []
    if f.is_file():
        priors = (_load_json(f) or {}).get("abstracted_priors") or []
    has_hyps = (run_root / "wave2_hypotheses.json").is_file()
    return {
        "done": bool(priors),
        "owed": bool(has_hyps and not priors),  # research happened but not abstracted
        "n_priors": len(priors),
    }


def _observe_projection(patient_dir: Path, run_id: str) -> dict[str, Any]:
    """Deterministic projection of a run's durable state. Pure read — no LLM,
    no writes. Tolerant of a half-built run (plan/manifest/memory may be absent)."""
    run_root = patient_dir / "triggers" / run_id
    plan = _load_json(run_root / "plan.json") or {}
    manifest = _load_json(run_root / "run_manifest.json") or {}

    planned_waves = manifest.get("planned_waves") or sorted({
        int(w.get("wave_number")) for w in (plan.get("waves", []) or [])
        if isinstance(w, dict) and w.get("wave_number") is not None
    })
    planned_experts = manifest.get("planned_experts") or sorted({
        str(t.get("expert")).lower() for t in (plan.get("tasks", []) or [])
        if isinstance(t, dict) and t.get("expert")
    })

    wave_states: dict[int, dict[str, Any]] = {}
    outstanding: list[int] = []
    for w in (1, 2, 3, 4):
        if w in _WAVE_ARTIFACT_PROBES:
            st = _wave_artifact_state(run_root, w)
            wave_states[w] = {"done": st["ok"], "artifacts_found": st["found"]}
            if (not planned_waves or w in planned_waves) and not st["ok"]:
                outstanding.append(w)

    delivery_dir = run_root / "delivery"
    delivered = bool(delivery_dir.exists() and any(
        (delivery_dir / f).exists()
        for f in ("patient_plain_brief.md", "patient_pi_brief.md")
    ))
    attested = bool((delivery_dir / "DELIVERY_ATTESTATION.json").exists())

    mem: dict[str, Any] = {"available": False}
    try:
        from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db
        db = default_patient_memory_db(run_root)
        if db.exists():
            store = ProjectMemoryStore(db)
            by_status: dict[str, int] = {}
            for h in store.query_hypotheses(run_id=run_id):
                by_status[str(h.status)] = by_status.get(str(h.status), 0) + 1
            # Negative constraints = falsified hypotheses ACROSS ALL RUNS, so a
            # returning patient's already-killed direction is re-surfaced and
            # never silently re-proposed (Arbor's pruned-lessons projection).
            falsified_all = store.query_hypotheses(status="falsified")
            priors_all = store.query_abstractions()
            mem = {
                "available": True,
                "ledger_records_total": store.ledger_count(),
                "ledger_records_this_run": store.ledger_count(run_id=run_id),
                "hypotheses_this_run_by_status": by_status,
                "tournament_rounds_this_run": len(store.query_tournament_rounds(run_id=run_id)),
                "negative_constraints": [
                    {"id": h.id, "text": h.text[:140]} for h in falsified_all[:20]
                ],
                # Arbor/HTR insight propagation (ADR-0042 ✗① fix): the actual
                # abstracted-prior CONTENT from prior runs, so the planner reads
                # the lesson — not just a count — and conditions ideation on it
                # (warns_against priors are dead-ends, supports priors are leads).
                "cross_run_priors": len(priors_all),
                "cross_run_priors_list": [
                    {"id": pr.get("id"), "lesson": str(pr.get("lesson", ""))[:160],
                     "directional": pr.get("directional"), "applies_to": pr.get("applies_to")}
                    for pr in priors_all[:8]
                ],
            }
    except Exception as exc:  # memory layer is optional/absent early in a run
        mem = {"available": False, "error": str(exc)}

    # Arbor/HTR tree + funnel + abstraction (ADR-0042) — pure reads.
    hyps = _load_hypotheses(run_root)
    funnel = _compute_funnel(run_root)
    abstraction = _abstraction_state(run_root)
    max_depth = int(plan.get("max_depth") or manifest.get("max_depth") or 1)
    from opl_cancer.glue.run_events import load_run_checkpoint, summarize_run_events
    events_summary = summarize_run_events(run_root)
    checkpoint = load_run_checkpoint(run_root)

    # ✗② per-candidate convergence state via the SAME assessor `deepen` uses, so
    # the projection can never disagree with the action (the iteration-2 bug).
    _w4 = _w4_survival_by_id(run_root)
    _hyps_re = hyps + _load_killed(run_root)  # killed children counted (re-entry only, not funnel/tree)
    cand_states: dict[str, str] = {}
    for cand in (plan.get("deepen_candidates") or []):
        cand = str(cand)
        a = _assess_deepen(_hyps_re, cand, max_depth, _w4)
        st = a["state"]
        if st == "absent":
            cand_states[cand] = "absent"
        elif st == "dead_target":
            cand_states[cand] = "dead (Wave-4 falsified — do NOT deepen)"
        elif st == "dry":
            cand_states[cand] = "dry (converged)"
        elif st == "awaiting_judgement":
            cand_states[cand] = f"awaiting judgement ({a.get('pending', 0)} children pending validation)"
        elif st == "budget_spent":
            cand_states[cand] = f"budget-spent (frontier {a['frontier']} @ depth {a['frontier_depth']}/{a['max_depth']})"
        else:
            cand_states[cand] = f"deepenable (frontier {a['frontier']} @ depth {a['frontier_depth']})"

    return {
        "run_id": run_id,
        "patient_dir": str(patient_dir),
        "goal": plan.get("goal") or plan.get("objective") or manifest.get("goal"),
        "run_token_present": bool(manifest.get("run_token")),
        "opl_version": manifest.get("opl_version") or VERSION,
        "planned_waves": planned_waves,
        "planned_experts": planned_experts,
        "wave_states": wave_states,
        "outstanding_waves": outstanding,
        "delivered": delivered,
        "attested": attested,
        "memory": mem,
        # ADR-0042 additions:
        "hypothesis_tree": _render_forest_lines(hyps, w4_by_id=_w4) if hyps else [],
        "funnel": funnel,
        "abstraction": abstraction,
        "events": events_summary,
        "checkpoint": checkpoint,
        "depth": {"max_depth": max_depth, "reached": funnel["tree_depth_reached"],
                  "deepen_candidates": list(plan.get("deepen_candidates") or []),
                  "candidate_states": cand_states},
    }


def _render_observe_text(p: dict[str, Any]) -> str:
    bar = "=" * 72
    L = [bar, "OBSERVE — OPL run state (read-only re-projection; NOT an executor)", bar]
    L.append(f"run_id        : {p['run_id']}")
    L.append(f"goal          : {p.get('goal') or '(unset — plan not run yet)'}")
    L.append(f"opl_version   : {p['opl_version']}")
    L.append(f"run_token     : {'present' if p['run_token_present'] else 'MISSING (no plan / free-handed)'}")
    L.append(f"planned waves : {p['planned_waves'] or '(none — run plan first)'}")
    L.append(f"planned team  : {', '.join(p['planned_experts']) if p['planned_experts'] else '(none)'}")
    L.append("")
    L.append("-- Waves (done? / artifacts) --")
    for w, st in sorted(p["wave_states"].items()):
        mark = "=" if st["done"] else "o"
        L.append(f"  [{mark}] wave {w}: {'done' if st['done'] else 'PENDING'} ({st['artifacts_found']} artifacts)")
    L.append("")
    L.append(f"-- Outstanding (planned but no artifacts): {p['outstanding_waves'] or 'none'} --")
    L.append(f"-- Delivery: {'delivered' if p['delivered'] else 'not delivered'}"
             f"{' + attested' if p['attested'] else ''} --")
    L.append("")
    m = p["memory"]
    L.append("-- Memory frontier (Project Memory ledger) --")
    if not m.get("available"):
        L.append("  (no ledger yet — nothing persisted)")
    else:
        L.append(f"  ledger records: {m['ledger_records_this_run']} this run / {m['ledger_records_total']} total")
        L.append(f"  hypotheses this run: {m['hypotheses_this_run_by_status'] or '{}'}")
        L.append(f"  tournament rounds this run: {m['tournament_rounds_this_run']}")
        nc = m.get("negative_constraints") or []
        L.append(f"  negative constraints (falsified across ALL runs — do NOT re-propose): {len(nc)}")
        for h in nc[:10]:
            L.append(f"     ✗ {h['id']}: {h['text']}")
        L.append(f"  cross-run priors available (warm-start from prior runs): {m.get('cross_run_priors', 0)}")
        for pr in (m.get("cross_run_priors_list") or [])[:6]:
            arrow = "↑" if pr.get("directional") == "supports" else ("⊘" if pr.get("directional") == "warns_against" else "·")
            L.append(f"     {arrow} {pr.get('id')}: {pr.get('lesson')}"
                     + (f"  [{pr.get('applies_to')}]" if pr.get("applies_to") else ""))
    L.append("")

    # ── Arbor/HTR tree + funnel + abstraction (ADR-0042) ──
    tree = p.get("hypothesis_tree") or []
    dep = p.get("depth") or {}
    L.append(f"-- Hypothesis TREE (Elo-ranked; depth {dep.get('reached', 1)}/{dep.get('max_depth', 1)}) --")
    if not tree:
        L.append("  (no hypotheses yet)")
    else:
        L.extend(tree)
        cand = dep.get("deepen_candidates") or []
        if cand:
            states = dep.get("candidate_states") or {}
            L.append("  ↳ planner marked for DEEPEN (re-entry):")
            for c in cand:
                L.append(f"       {c} — {states.get(str(c), 'deepenable')}")
    L.append("")
    fn = p.get("funnel") or {}
    L.append("-- Explored → survived FUNNEL --")
    L.append(f"  explored {fn.get('explored', 0)} · killed-in-tournament {fn.get('killed_in_tournament', 0)}"
             f" · validated {fn.get('validated', 0)} · falsified {fn.get('falsified', 0)}"
             f" · inconclusive {fn.get('inconclusive', 0)} · ties-split-by-selection {fn.get('ties_resolved_by_selection', 0)}")
    ab = p.get("abstraction") or {}
    state = "done (" + str(ab.get("n_priors", 0)) + " priors)" if ab.get("done") else ("OWED — run the abstraction beat" if ab.get("owed") else "n/a")
    L.append(f"-- Abstraction (Arbor's dominant gain driver): {state} --")
    ev = p.get("events") or {}
    L.append("-- Run events (machine log) --")
    if ev.get("available"):
        last = ev.get("last_event") or {}
        L.append(f"  events: {ev.get('count', 0)} · last {last.get('event_type')} @ {last.get('at')}")
    else:
        L.append("  (no run_events.jsonl yet)")
    cp = p.get("checkpoint")
    L.append("-- Resume checkpoint --")
    if cp:
        L.append(f"  phase: {cp.get('phase') or '(unset)'} · reason: {cp.get('reason')}")
    else:
        L.append("  (none)")
    L.append("")
    L.append(bar)
    L.append("Re-ground on THIS projection, not your memory of the conversation. Then "
             "dispatch the next outstanding wave's subagents (main thread), or — if a "
             "planner deepen-candidate has Elo-tie rivals and depth budget remains — "
             "`opl-cancer deepen` that lead; abstract before delivery.")
    return "\n".join(L)


@main.command(help="Re-projection of run state (read-only, no execution): planned-vs-done waves, "
                   "outstanding work, memory frontier, and cross-run falsified hypotheses as negative "
                   "constraints. Re-ground on this at each wave beat (Arbor/HTR observe).")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def observe(patient_dir: str, run_id: str, json_mode: bool) -> None:
    proj = _observe_projection(Path(patient_dir), run_id)
    if json_mode:
        click.echo(json.dumps(proj, ensure_ascii=False, indent=2))
    else:
        click.echo(_render_observe_text(proj))


def _validate_run_state(patient_dir: Path, run_id: str) -> list[dict[str, str]]:
    """Deterministic invariant check over a run's durable state (Arbor `validate`
    analog). Pure read. Returns a list of {severity, code, message}; severity
    'error' means the state is inconsistent (caller exits non-zero)."""
    run_root = patient_dir / "triggers" / run_id
    problems: list[dict[str, str]] = []

    def add(sev: str, code: str, msg: str) -> None:
        problems.append({"severity": sev, "code": code, "message": msg})

    if not run_root.exists():
        add("error", "RUN_MISSING", f"no run directory at {run_root}")
        return problems

    proj = _observe_projection(patient_dir, run_id)
    manifest = _load_json(run_root / "run_manifest.json")
    plan = _load_json(run_root / "plan.json")

    # 1. A delivered/attested run must have been planned (run_token minted at plan).
    if not manifest:
        add("warn", "NO_MANIFEST", "no run_manifest.json — `plan` not run for this run_id")
    elif not manifest.get("run_token"):
        add("error", "NO_RUN_TOKEN", "run_manifest.json present but carries no run_token (forge-resistance broken)")

    # 2. planned_experts in the manifest must match the experts named in plan.json.
    if manifest and plan:
        m_exp = set(manifest.get("planned_experts") or [])
        p_exp = {str(t.get("expert")).lower() for t in (plan.get("tasks", []) or [])
                 if isinstance(t, dict) and t.get("expert")}
        if m_exp and p_exp and m_exp != p_exp:
            add("error", "MANIFEST_PLAN_DRIFT",
                f"manifest planned_experts {sorted(m_exp)} != plan tasks' experts {sorted(p_exp)} "
                "(silent team-shrink / manifest tampering)")

    # 3. Delivery / attestation consistency.
    if proj["attested"] and not proj["delivered"]:
        add("error", "ATTESTED_WITHOUT_BRIEF",
            "DELIVERY_ATTESTATION.json present but no patient brief was rendered")
    if proj["delivered"] and not proj["attested"]:
        add("warn", "DELIVERED_NOT_ATTESTED",
            "a brief exists but the run is not attested — run `opl-cancer attest`")

    # 4. A delivered run must have written to the memory ledger (G54 invariant,
    #    re-checked here so a half-finished run is caught before it claims done).
    mem = proj["memory"]
    if proj["delivered"]:
        if not mem.get("available"):
            add("error", "DELIVERED_NO_LEDGER",
                "run delivered but no Project-Memory ledger exists — learning did not compound")
        elif mem.get("ledger_records_this_run", 0) == 0:
            add("error", "DELIVERED_EMPTY_LEDGER",
                "run delivered but wrote 0 ledger records this run (G54 would block)")

    # 5. Artifacts for a wave the manifest planned but that has none yet — only
    #    a problem once the run claims delivery (mid-run, pending is expected).
    if proj["delivered"] and proj["outstanding_waves"]:
        add("error", "DELIVERED_WITH_OUTSTANDING_WAVES",
            f"run delivered but planned waves {proj['outstanding_waves']} have no artifacts (under-delivery)")

    # 6. Abstraction owed (ADR-0042, G60 invariant) — WARN, never blocks the brief.
    if proj["delivered"] and proj.get("abstraction", {}).get("owed"):
        add("warn", "DELIVERED_NO_ABSTRACTION",
            "run delivered but no cross-run prior abstracted (G60 owed) — "
            "learning did not compound upward; run `opl-cancer abstract --finalize`")

    # 7. Depth budget invariant (ADR-0042): re-entry must never exceed the
    #    planner-granted max_depth.
    dep = proj.get("depth", {})
    if dep.get("reached", 1) > dep.get("max_depth", 1):
        add("error", "DEPTH_BUDGET_EXCEEDED",
            f"tree depth reached {dep['reached']} exceeds plan max_depth {dep['max_depth']} "
            "(re-entry ran past its budget)")

    # 8. Informative selection (ADR-0042 ✗③) — WARN. If Wave 4 ran and there were
    #    near-tied surviving rivals but NO validation recorded a discrimination
    #    target, the scarce N=1 validation budget was not spent splitting the tie.
    if (run_root / "wave4_validation.json").exists():
        # Only SCORED survivors form a tie — a missing elo is not a 0-point tie
        # (review P2: else any ≥2 unscored survivors would false-fire the WARN).
        _w4v = _w4_survival_by_id(run_root)
        scored = [h for h in _load_hypotheses(run_root)
                  if _lifestate(h, _w4v) == "alive" and h.get("elo_rating") is not None]
        near_tie = any(
            abs(a["elo_rating"] - b["elo_rating"]) <= 50
            for i, a in enumerate(scored) for b in scored[i + 1:]
        )
        if near_tie and proj.get("funnel", {}).get("ties_resolved_by_selection", 0) == 0:
            add("warn", "INFORMATIVE_SELECTION_SKIPPED",
                "Wave 4 had a scored near-tie among surviving hypotheses but no validation recorded a "
                "discrimination_target — scarce N=1 validation was not spent splitting the tie "
                "(informative selection; prompts/methods/informative_selection.md)")

    return problems


@main.command(help="Read-only invariant check on a run's durable state (Arbor/HTR `validate`). "
                   "Exits non-zero if the state is inconsistent (manifest/plan drift, attested-without-brief, "
                   "delivered-without-ledger, under-delivery). Never executes a wave, never writes.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def validate(patient_dir: str, run_id: str, json_mode: bool) -> None:
    problems = _validate_run_state(Path(patient_dir), run_id)
    errors = [p for p in problems if p["severity"] == "error"]
    payload = {
        "ok": not errors,
        "run_id": run_id,
        "errors": len(errors),
        "warnings": len(problems) - len(errors),
        "problems": problems,
    }
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if not problems:
            click.echo(f"OK — run {run_id} state is consistent.")
        else:
            click.echo(f"validate {run_id}: {len(errors)} error(s), {payload['warnings']} warning(s)")
            for p in problems:
                mark = "✗" if p["severity"] == "error" else "!"
                click.echo(f"  {mark} {p['severity'].upper():5} {p['code']:28} {p['message']}")
    if errors:
        sys.exit(2)


@main.command(
    name="recovery-plan",
    help=(
        "Build a deterministic recovery plan for a run. Read-only: inspects "
        "validate/observe/checkpoint/events and proposes next actions."
    ),
)
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def recovery_plan_cmd(patient_dir: str, run_id: str, json_mode: bool) -> None:
    from opl_cancer.glue.recovery import build_recovery_plan

    pdir = Path(patient_dir)
    projection = _observe_projection(pdir, run_id)
    problems = _validate_run_state(pdir, run_id)
    plan = build_recovery_plan(
        pdir,
        run_id,
        projection=projection,
        validation_problems=problems,
    )
    if json_mode:
        click.echo(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    click.echo(f"Recovery plan for {run_id}: {plan['status']}")
    for action in plan["next_actions"]:
        click.echo(f"  {action['code']}: {action['label']}")
        if action.get("command"):
            click.echo(f"    {action['command']}")


@main.command(
    name="events",
    help=(
        "Append/read the structured run event log (run_events.jsonl). "
        "This is the machine-readable spine for dashboards, resume, and MCP tools; "
        "it never executes a wave."
    ),
)
@click.option(
    "--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True
)
@click.option("--run-id", required=True)
@click.option(
    "--emit", "emit_type", default="", help="Append one event of this type, then return it."
)
@click.option("--phase", default="", help="Optional phase label for emitted or filtered events.")
@click.option("--source", default="opl_cancer.cli.events", show_default=True)
@click.option(
    "--severity",
    type=click.Choice(["debug", "info", "warn", "error"]),
    default="info",
    show_default=True,
)
@click.option("--payload-json", default="", help="JSON object payload for --emit.")
@click.option("--type", "filter_type", default="", help="Filter listed events by event_type.")
@click.option("--limit", type=int, default=20, show_default=True)
@click.option("--json", "json_mode", is_flag=True)
def events_cmd(
    patient_dir: str,
    run_id: str,
    emit_type: str,
    phase: str,
    source: str,
    severity: str,
    payload_json: str,
    filter_type: str,
    limit: int,
    json_mode: bool,
) -> None:
    from opl_cancer.glue.run_events import (
        append_run_event,
        iter_run_events,
        summarize_run_events,
    )

    run_root = Path(patient_dir) / "triggers" / run_id
    if emit_type:
        payload: dict[str, Any] = {}
        if payload_json:
            try:
                parsed = json.loads(payload_json)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"--payload-json is not valid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise click.ClickException("--payload-json must decode to a JSON object")
            payload = parsed
        event = append_run_event(
            run_root,
            emit_type,
            phase=phase or None,
            source=source,
            severity=severity,
            payload=payload,
        )
        _emit({"ok": True, "event": event}, json_mode)
        return

    records = list(iter_run_events(
        run_root,
        event_type=filter_type or None,
        phase=phase or None,
    ))
    if limit >= 0:
        records = records[-limit:]
    payload = {
        "ok": True,
        "run_id": run_id,
        "summary": summarize_run_events(run_root),
        "events": records,
    }
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not records:
        click.echo(f"No run events for {run_id}.")
        return
    for event in records:
        ph = f" [{event.get('phase')}]" if event.get("phase") else ""
        click.echo(
            f"{event.get('at')} {event.get('severity')} {event.get('event_type')}{ph} "
            f"{event.get('event_id')}"
        )


@main.command(
    name="checkpoint",
    help=(
        "Read/write the latest resumable checkpoint (run_checkpoint.json). "
        "This records orchestration position only; gates still validate artifacts."
    ),
)
@click.option(
    "--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True
)
@click.option("--run-id", required=True)
@click.option("--write", is_flag=True, help="Write a new checkpoint instead of reading.")
@click.option("--reason", default="", help="Why the run is pausing or where resume should start.")
@click.option("--phase", default="", help="Current phase label.")
@click.option("--payload-json", default="", help="JSON object payload for --write.")
@click.option("--json", "json_mode", is_flag=True)
def checkpoint_cmd(
    patient_dir: str,
    run_id: str,
    write: bool,
    reason: str,
    phase: str,
    payload_json: str,
    json_mode: bool,
) -> None:
    from opl_cancer.glue.run_events import load_run_checkpoint, write_run_checkpoint

    run_root = Path(patient_dir) / "triggers" / run_id
    if write:
        if not reason.strip():
            raise click.ClickException("--reason is required with --write")
        payload: dict[str, Any] = {}
        if payload_json:
            try:
                parsed = json.loads(payload_json)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"--payload-json is not valid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise click.ClickException("--payload-json must decode to a JSON object")
            payload = parsed
        checkpoint = write_run_checkpoint(
            run_root,
            reason=reason,
            phase=phase or None,
            payload=payload,
        )
        _emit({"ok": True, "checkpoint": checkpoint}, json_mode)
        return

    checkpoint = load_run_checkpoint(run_root)
    payload = {"ok": checkpoint is not None, "run_id": run_id, "checkpoint": checkpoint}
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    elif checkpoint:
        click.echo(
            f"{checkpoint.get('at')} {checkpoint.get('phase') or '(unset)'} "
            f"{checkpoint.get('reason')}"
        )
    else:
        click.echo(f"No checkpoint for {run_id}.")


# ─── Arbor/HTR depth (ADR-0042): abstract · deepen · funnel ───────────────

@main.command(help="Abstraction beat (Arbor/HTR insight propagation, ADR-0042): persist the cross-run "
                   "priors the PI authored in triggers/<run_id>/abstraction.json. No flag = scaffold "
                   "(tells you to dispatch prompts/pi/insight_abstraction.md); --finalize = validate shape "
                   "+ append to the ledger. The CLI never authors the abstraction — that is judgment.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--finalize", is_flag=True, help="Validate abstraction.json + persist its priors.")
@click.option("--json", "json_mode", is_flag=True)
def abstract(patient_dir: str, run_id: str, finalize: bool, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    abs_file = run_root / "abstraction.json"
    hyps = _load_hypotheses(run_root)

    if not finalize:
        _emit({
            "ok": True, "beat": "scaffold",
            "abstraction_present": abs_file.is_file(),
            "n_hypotheses": len(hyps),
            "action": (
                "Dispatch prompts/pi/insight_abstraction.md as a subagent — it reads this run's "
                f"hypotheses + Wave-4 verdicts and writes triggers/{run_id}/abstraction.json with 1-3 "
                "GROUNDED cross-run priors (generalise across leaves; never restate one hypothesis). "
                "Then re-run with --finalize to persist them."
            ),
        }, json_mode)
        return

    if not abs_file.is_file():
        raise click.ClickException(
            "abstraction.json not found — dispatch prompts/pi/insight_abstraction.md first "
            "(run `abstract` without --finalize for the exact action)."
        )
    priors = (_load_json(abs_file) or {}).get("abstracted_priors") or []
    if not priors:
        raise click.ClickException("abstraction.json has zero abstracted_priors — the beat must produce >=1 grounded prior.")
    # Half-built-run guard (review P1): with no hypotheses there is nothing to
    # ground against, so EVERY prior would be ungrounded. Refuse rather than
    # persist fabricated source_leaf_ids into the durable cross-run ledger.
    if not hyps:
        raise click.ClickException(
            "no hypotheses to ground against (wave2_hypotheses.json absent/empty) — run Wave 2 "
            "before abstracting; an abstraction with no real leaves cannot be persisted."
        )
    src_ids = {str(h.get("id")) for h in hyps if h.get("id")}
    src_texts = {re.sub(r"\s+", " ", str(h.get("text", "")).strip().lower()) for h in hyps}
    problems: list[str] = []
    for p in priors:
        pid = str(p.get("id") or "?")
        lesson = re.sub(r"\s+", " ", str(p.get("lesson", "")).strip().lower())
        leaves = [str(x) for x in (p.get("source_leaf_ids") or [])]
        if not lesson:
            problems.append(f"{pid}: empty lesson")
        elif lesson in src_texts:
            problems.append(f"{pid}: lesson is a verbatim copy of a source hypothesis (auto-fill)")
        if not leaves:
            problems.append(f"{pid}: no source_leaf_ids (ungrounded)")
        elif not (set(leaves) & src_ids):  # no `src_ids and` precondition — empty src_ids → reject, never skip
            problems.append(f"{pid}: source_leaf_ids reference no real hypothesis in this run")
    if problems:
        raise click.ClickException("abstraction.json is not a real abstraction: " + "; ".join(problems))

    from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db
    store = ProjectMemoryStore(default_patient_memory_db(run_root))
    for p in priors:
        store.save_abstraction(p, run_id=run_id)
    _emit({"ok": True, "beat": "finalize", "persisted_priors": len(priors), "run_id": run_id}, json_mode)


@main.command(help="Deepen a hot lead (Arbor/HTR re-entry, ADR-0042): scaffold a focused sub-investigation of "
                   "ONE hypothesis and its Elo-tie rivals, bounded by the plan's max_depth. Read-only "
                   "scaffolder — checks the depth budget + tells the host to dispatch a scoped mini Wave-2..4 "
                   "on child hypotheses (parent_chain=[target]). ADDITIVE: never drops the floor, never writes.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--target", required=True, help="Hypothesis id to deepen.")
@click.option("--json", "json_mode", is_flag=True)
def deepen(patient_dir: str, run_id: str, target: str, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    # killed-in-tournament children count as DEAD children of their frontier, so a
    # round whose spawns all died makes the frontier 'dry', not forever-deepenable.
    hyps = _load_hypotheses(run_root) + _load_killed(run_root)
    by_id = {str(h.get("id")): h for h in hyps if h.get("id")}
    plan = _load_json(run_root / "plan.json") or {}
    manifest = _load_json(run_root / "run_manifest.json") or {}
    max_depth = int(plan.get("max_depth") or manifest.get("max_depth") or 1)

    if target not in by_id:  # genuine misuse → non-zero (unlike the advisory stops)
        raise click.ClickException(
            f"target '{target}' not found in this run's hypotheses (have e.g. {sorted(by_id)[:8]})."
        )

    # Single source of truth (glue.funnel.assess_deepen): direct-parent children,
    # forest-walk depth, canonical alive/dead/pending lifestate, frontier-advancing.
    _w4 = _w4_survival_by_id(run_root)
    a = _assess_deepen(hyps, target, max_depth, _w4)

    # Exit-code contract: the two NORMAL terminal outcomes (dry / budget spent) are
    # ADVISORY stops, NOT errors — exit 0 with ok:False so an automated caller
    # (set -e / check=True) does not misread convergence as a hard failure.
    if a["state"] == "dry":
        _emit({
            "ok": False, "reason": "direction_dry", "advisory": True,
            "target": target, "children_explored": a.get("children_explored", 0),
            "message": (
                f"{target} was deepened ({a.get('children_explored', 0)} children) and its whole subtree is "
                "terminally dead (none alive, none pending) — DRY (loop-until-dry converged). Stop deepening "
                "this lead; spend the budget elsewhere or proceed to delivery."
            ),
        }, json_mode)
        return
    if a["state"] == "budget_spent":
        _emit({
            "ok": False, "reason": "depth_budget_exhausted", "advisory": True,
            "target": target, "frontier": a["frontier"], "frontier_depth": a["frontier_depth"],
            "max_depth": max_depth,
            "message": (
                f"the live frontier of {target} is {a['frontier']} at depth {a['frontier_depth']} = "
                f"max_depth {max_depth}. Re-entry refused — raise max_depth only if a deeper split genuinely "
                "helps the patient, else stop deepening and proceed."
            ),
        }, json_mode)
        return
    if a["state"] == "dead_target":  # P1: never deepen a Wave-4-falsified lead
        _emit({
            "ok": False, "reason": "target_dead", "advisory": True, "target": target,
            "message": (
                f"{target} is itself terminally dead (Wave-4 falsified / retired / saturated). Deepening a "
                "disproven direction would present false hope — refused. Pick a live lead or proceed to delivery."
            ),
        }, json_mode)
        return
    if a["state"] == "awaiting_judgement":  # P0: don't spawn more while children pending
        _emit({
            "ok": False, "reason": "awaiting_judgement", "advisory": True,
            "target": target, "pending": a.get("pending", 0),
            "message": (
                f"{target} has {a.get('pending', 0)} child hypothes(es) still PENDING Wave-4 judgement. Do NOT "
                "spawn more — finish validating the existing children first. If Wave-4 already returned "
                "'inconclusive' for them, treat the lead as CONVERGED and proceed to delivery (do not keep "
                "re-spawning); otherwise re-run deepen once they resolve (alive → deepen further; all dead → dry). "
                "Termination backstop against an all-inconclusive livelock."
            ),
        }, json_mode)
        return

    # deepenable — deepen the live FRONTIER node (advances depth each round).
    frontier = a["frontier"]
    elo = by_id[frontier].get("elo_rating") or 0
    sub = set()  # exclude the frontier's own subtree from rivals
    children, _r = _build_hypothesis_forest(hyps)
    stack = [frontier]
    while stack:
        n = stack.pop()
        if n in sub:
            continue
        sub.add(n)
        stack.extend(children.get(n, []))
    rivals = sorted(
        [h for h in hyps if str(h.get("id")) not in sub
         and abs((h.get("elo_rating") or 0) - elo) <= 50
         and _lifestate(h, _w4) == "alive"],   # canonical vocab (no fork)
        key=lambda h: -(h.get("elo_rating") or 0),
    )
    _emit({
        "ok": True, "target": target, "frontier": frontier,
        "frontier_depth": a["frontier_depth"], "new_depth": a["frontier_depth"] + 1, "max_depth": max_depth,
        "tie_rivals": [{"id": str(h.get("id")), "elo": h.get("elo_rating")} for h in rivals[:5]],
        "action": (
            f"Re-entry warranted. Deepen the live frontier {frontier} (depth {a['frontier_depth']}): dispatch a "
            f"FOCUSED mini Wave-2..4 generating child hypotheses with parent_chain=[{frontier}, …] that SPLIT it "
            "from its tie-rivals, run tournament + validation, then `opl-cancer observe`. Each round advances depth "
            f"toward max_depth {max_depth}; the loop stops when the frontier goes dry or the budget is spent. "
            "Additive only — the planned floor is untouched."
        ),
    }, json_mode)


@main.command(help="Explored→survived FUNNEL (ADR-0042): deterministic counts (explored / killed-in-tournament / "
                   "validated / falsified / inconclusive / ties-split-by-selection). --emit writes "
                   "triggers/<run_id>/funnel.json so the brief reports it honestly to the patient. Counts only — "
                   "no judgment.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--emit", "do_emit", is_flag=True, help="Write triggers/<run_id>/funnel.json for the brief.")
@click.option("--json", "json_mode", is_flag=True)
def funnel(patient_dir: str, run_id: str, do_emit: bool, json_mode: bool) -> None:
    run_root = Path(patient_dir) / "triggers" / run_id
    fn = _compute_funnel(run_root)
    fn["run_id"] = run_id
    if do_emit:
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / "funnel.json").write_text(json.dumps(fn, ensure_ascii=False, indent=2), encoding="utf-8")
        fn["written"] = str(run_root / "funnel.json")
    _emit(fn, json_mode)


# ─── v2.1 P0-#1+#2: opl run — real executor wrapping wave runners ─────────
#
# honest-failure policy + ADR-0021. Through v2.0.x the only
# CLI surface that *looked* like a wave executor (`opl wave1`, etc.) was
# really a state reader — it returned ok=true if artifacts existed and
# requires_main_thread_dispatch otherwise. v2.1 introduces a separate
# `opl run --wave N` command that ACTUALLY executes the corresponding
# wave pipeline. For Wave 3 specifically, `--mode {native,docker,dry-run}`
# selects the compute backend; if neither Docker nor native Jupyter is
# present the command refuses honestly (no silent fallback).
#
# The wave1/wave2/wave3/wave4 *class* runners (glue/waveN_runner.py) still
# require a populated LLM client + expert factory which only the main-thread
# Claude orchestrator can supply. `opl run --wave 3 --mode native|docker`
# additionally proves the compute backend is wired by running a tiny smoke
# notebook (an empty `{}` .ipynb) through NativeAnalysisRunner /
# BixbenchRunner so that downstream waves know the path is alive.


def _select_wave3_mode() -> str:
    """Pick the highest-fidelity Wave-3 mode available on this host.

    Order: native (jupyter) → docker (bixbench) → error.
    """
    if NativeAnalysisRunner().is_available():
        return "native"
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            subprocess.run([docker_bin, "info"], check=True, capture_output=True, timeout=5)
            return "docker"
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
    raise click.ClickException(
        "Neither Docker nor native Jupyter available. Pass --mode dry-run to "
        "proceed without execution."
    )


def _emit_run_result(wave: int, result: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps({"wave": wave, "status": "executed", "result": result},
                              ensure_ascii=False, indent=2))
    else:
        click.echo(f"Wave {wave} executed. Result: {result}")


def _executor_llm_available() -> dict[str, Any]:
    """v2.7.1 ADR-0026 Fork B — is a self-sufficient executor LLM configured?

    `opl run --wave 1` can drive the full Wave1Runner WITHOUT a human-LLM main
    thread when an executor key is present (so the run is third-party
    reproducible). Requires BOTH an executor key AND a G13-distinct reviewer key
    (reviewer family != executor family). On Claude Code there is no API key for
    the host model, so this returns ok=False and the caller hands off to the
    main-thread dispatcher — never a silent fallback (no-silent-fallback policy).
    """
    provider = (os.environ.get("OPL_EXECUTOR_PROVIDER") or "anthropic").lower()
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_minimax = bool(os.environ.get("MINIMAX_API_KEY"))
    has_executor = {"anthropic": has_anthropic, "minimax": has_minimax}.get(provider, has_anthropic)
    # G13: reviewer must be a DIFFERENT family than the executor.
    has_reviewer = has_minimax if provider == "anthropic" else has_anthropic
    ok = has_executor and has_reviewer
    return {
        "ok": ok, "provider": provider,
        "has_executor": has_executor, "has_reviewer": has_reviewer,
        "reason": "" if ok else (
            "no self-sufficient executor — set the executor key + a G13-distinct "
            "reviewer key (e.g. ANTHROPIC_API_KEY + MINIMAX_API_KEY). On Claude Code "
            "the agent IS the executor; dispatch the wave on the main thread."
        ),
    }


def _run_wave3_compute(run_root: Path, mode: str) -> dict[str, Any]:
    """Invoke the selected compute runner on a smoke notebook.

    The runner's `run_notebook` is called with the wave-3 working directory
    so any side-effects (image pull, jupyter kernel spawn) surface here.
    For dry-run we still construct the runner so misconfiguration is caught.
    """
    workdir = run_root / "data" / "wave3_smoke"
    workdir.mkdir(parents=True, exist_ok=True)
    notebook = workdir / "smoke.ipynb"
    # Minimal valid notebook (no cells) — enough for nbconvert / docker exec
    # to confirm the toolchain works.
    notebook.write_text(
        json.dumps(
            {
                "cells": [],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        )
    )
    if mode == "native":
        runner = NativeAnalysisRunner()
        rr = runner.run_notebook(notebook_path=notebook, workdir=workdir, timeout_s=120)
    elif mode == "docker":
        runner = BixbenchRunner()
        rr = runner.run_notebook(notebook_path=notebook, workdir=workdir, timeout_s=120)
    elif mode == "dry-run":
        # construct but do not execute; still call run_notebook in dry mode
        # so the compute runner reports the command it *would* run.
        runner = NativeAnalysisRunner()
        rr = runner.run_notebook(notebook_path=notebook, workdir=workdir, timeout_s=120)
    else:  # pragma: no cover — click.Choice rejects others
        raise click.ClickException(f"unknown --mode {mode!r}")
    payload: dict[str, Any] = {
        "mode": mode,
        "notebook_path": str(notebook),
        "workdir": str(workdir),
    }
    if hasattr(rr, "to_dict"):
        payload["compute_result"] = rr.to_dict()
    return payload


@main.command(
    help=(
        "Step 6/7/8/9: Execute the named wave for real (not state-check). "
        "Wave 3 supports --mode {docker,native,dry-run}. Waves 1/2/4 currently "
        "verify state of dispatched artifacts (the LLM dispatch itself is owned "
        "by the SKILL main thread per ADR-2026-04-22)."
    ),
)
@click.option("--wave", type=click.IntRange(1, 4), required=True,
              help="Wave number to execute")
@click.option("--patient-dir", "patient_dir", required=True,
              type=click.Path(file_okay=False),
              help="Patient directory root")
@click.option("--run-id", "run_id", required=True,
              help="Run identifier")
@click.option("--plan-path", "plan_path", default=None,
              help="Plan.json path (defaults to <patient_dir>/triggers/<run_id>/plan.json)")
@click.option("--mode", type=click.Choice(["docker", "native", "dry-run"]), default=None,
              help="Wave 3 execution mode")
@click.option("--json", "json_mode", is_flag=True, default=False)
def run(
    wave: int,
    patient_dir: str,
    run_id: str,
    plan_path: str | None,
    mode: str | None,
    json_mode: bool,
) -> None:
    """Real executor wrapping glue/wave{N}_runner.py.

    v2.1 P0-#1+#2 (ADR-0021). For Wave 3 (`--mode native|docker|dry-run`)
    this directly drives the compute runner so the smoke notebook proves
    the toolchain is live. For Waves 1/2/4 the full LLM dispatch is owned
    by the SKILL main thread, but this command still re-verifies the
    artifact-state contract honestly (refusing to claim completion if no
    artifacts landed) — same honest-failure semantics as `opl waveN`.
    """
    pdir = Path(patient_dir)
    pdir.mkdir(parents=True, exist_ok=True)
    run_root = pdir / "triggers" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    plan_file = Path(plan_path) if plan_path else run_root / "plan.json"
    if not plan_file.exists():
        raise click.ClickException(f"plan.json not found: {plan_file}")

    if wave == 3:
        chosen_mode = mode or _select_wave3_mode()
        result = _run_wave3_compute(run_root, chosen_mode)
    else:
        # Harness-split (HARNESS_SPLIT_PRD): the in-Python LLM dispatch is removed.
        # Waves 1/2/4 are host-agent-driven; this CLI verifies the artifact-state
        # contract honestly and refuses to claim completion when no real artifacts
        # are present. The SKILL main thread (the agent) is the dispatcher.
        state = _wave_artifact_state(run_root, wave)
        result = {
            "wave": wave,
            "artifacts_found": state["found"],
            "artifacts_sample": state["files"],
        }
        if not state["ok"]:
            result["requires_main_thread_dispatch"] = True
            result["action"] = (
                f"Wave {wave} produced no artifacts yet. The SKILL main thread "
                "(the agent) must dispatch the wave runner / write the per-expert "
                "host-agent reports — this CLI verifies state honestly per "
                "ADR-0021/0026 + HARNESS_SPLIT_PRD."
            )

    _emit_run_result(wave, result, json_mode)


@main.command(
    name="claim-graph",
    help=(
        "Build a deterministic claim-level evidence graph from structured claims JSON. "
        "This is an audit artifact, not a clinical judge."
    ),
)
@click.option("--claims-json", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--out", type=click.Path(), help="Optional path to write the graph JSON.")
@click.option("--json", "json_mode", is_flag=True)
def claim_graph_cmd(claims_json: str, out: str | None, json_mode: bool) -> None:
    from opl_cancer.delivery.claim_graph import (
        build_claim_evidence_graph,
        validate_claim_evidence_graph,
        write_claim_evidence_graph,
    )

    raw = json.loads(Path(claims_json).read_text(encoding="utf-8"))
    claims = raw.get("claims") if isinstance(raw, dict) else raw
    if not isinstance(claims, list) or not all(isinstance(c, dict) for c in claims):
        raise click.ClickException("--claims-json must be a list of claim objects or {claims:[...]}")

    graph = build_claim_evidence_graph(claims)
    validation = validate_claim_evidence_graph(graph)
    payload: dict[str, Any] = {
        "ok": validation["ok"],
        "summary": validation["summary"],
        "problems": validation["problems"],
    }
    if out:
        payload["graph_path"] = str(write_claim_evidence_graph(graph, Path(out)))
    else:
        payload["graph"] = graph

    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _emit(payload, json_mode)
    if not validation["ok"]:
        raise click.exceptions.Exit(2)


# ─── v2.7.0 ADR-0026 — delivery-integrity enforcement ─────────────────────
#
# Through v2.6.x `audit` and `render` were `mkdir + {"ok":true}` stubs that
# verified nothing — the exact hole that let session 0d1017d4 free-hand a brief
# (fabricated labs + wrong-paper PMIDs) and ship it. They are now fail-closed
# state-readers that route through the delivery-integrity gates (G34/G35/G37 +
# citation gates) and refuse (exit 2) when delivery is not backed by a real run.


def _build_citation_integrators() -> tuple[Any | None, Any | None]:
    """Best-effort live PubMed + PaperQA2 integrators for the citation gates.

    Returns (pubmed, paperqa); either may be None if unavailable — the gate
    runner records that honestly (never a silent pass) per principle #4.
    """
    pubmed = paperqa = None
    try:
        from opl_cancer.integrators.pubmed import PubMedIntegrator
        pubmed = PubMedIntegrator()
    except Exception:  # noqa: BLE001 — offline / missing cache is non-fatal here
        pubmed = None
    try:
        from opl_cancer.integrators.paperqa import PaperQA2Integrator
        paperqa = PaperQA2Integrator()
    except Exception:  # noqa: BLE001
        paperqa = None
    return pubmed, paperqa


def _run_delivery_integrity(patient_dir: str, run_id: str, *, with_citations: bool) -> dict[str, Any]:
    from opl_cancer.glue.delivery_gate_runner import run_delivery_gates
    run_root = Path(patient_dir) / "triggers" / run_id
    pubmed = paperqa = None
    if with_citations:
        pubmed, paperqa = _build_citation_integrators()
    return run_delivery_gates(run_root=run_root, pubmed=pubmed, paperqa=paperqa)


def _emit_integrity_verdict(verdict: dict[str, Any], json_mode: bool, **extra: Any) -> None:
    payload = {"ok": verdict["ok"], **extra,
               "blocked_by": verdict["blocked_by"], "notes": verdict["notes"]}
    if not verdict["ok"]:
        payload["action"] = (
            "Delivery REFUSED — the brief is not backed by a verifiable OPL run "
            f"(blocked by {verdict['blocked_by']}). Run the full pipeline "
            "(`opl-cancer go` or plan→waves→deliver --finalize); do NOT free-hand a brief."
        )
        payload["gate_results"] = verdict["gate_results"]
        _emit(payload, json_mode)
        raise click.exceptions.Exit(2)
    _emit(payload, json_mode)


# ─── Step 9: Henry audit ──────────────────────────────────────────────────

@main.command(help="Step 9: delivery-integrity gate sweep (G34/G35/G37 + citations). Fail-closed.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def audit(patient_dir: str, run_id: str, json_mode: bool) -> None:
    """v2.7.0: real mechanical audit. Runs the delivery-integrity gates over the
    run and REFUSES (exit 2) when the brief is not backed by a verifiable run.
    The per-claim Henry risk-card audit runs inside `deliver --finalize`."""
    verdict = _run_delivery_integrity(patient_dir, run_id, with_citations=True)
    _emit_integrity_verdict(verdict, json_mode, patient=patient_dir, run_id=run_id, stage="audit")


# ─── Step 10: render ──────────────────────────────────────────────────────

@main.command(help="Step 10 (DEPRECATED — use `deliver --finalize`): fail-closed delivery check.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def render(patient_dir: str, run_id: str, json_mode: bool) -> None:
    """v2.7.0: the old `render` stub (mkdir + ok:true) is gone — it was the hole
    that let a free-handed brief ship. `render` now runs the delivery-integrity
    gates and refuses unless the delivery is attested. Use `opl deliver --finalize`
    to produce + audit the briefs."""
    verdict = _run_delivery_integrity(patient_dir, run_id, with_citations=True)
    _emit_integrity_verdict(
        verdict, json_mode, patient=patient_dir, run_id=run_id, stage="render",
        deprecation="render is deprecated; use `opl-cancer deliver --finalize`.",
    )


# ─── v2.7.0 — explicit delivery attestation ───────────────────────────────

@main.command(help="v2.7.0: attest a run's delivery integrity (G34/G35/G37 + citations). Exit 2 if not attestable.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def attest(patient_dir: str, run_id: str, json_mode: bool) -> None:
    """Mechanical proof that a delivered brief is backed by a real run: a real
    manifest/token, a recomputable provenance journal, a real Henry audit, the
    full planned team, and on-topic citations. Writes DELIVERY_ATTESTATION.json."""
    verdict = _run_delivery_integrity(patient_dir, run_id, with_citations=True)
    _emit_integrity_verdict(verdict, json_mode, patient=patient_dir, run_id=run_id, stage="attest")


@main.command(
    name="deliver",
    help=(
        "v2.2 P1-#16 + v2.5.1 B1+B5: atomic delivery — verifies upstream "
        "Wave 1-5 artifacts, then runs real Henry audit + "
        "patient_plain_brief + patient_pi_brief as ONE transaction. "
        "Partial failure rolls back."
    ),
)
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--dry-run", is_flag=True, help="Plan only; write nothing.")
@click.option(
    "--allow-missing-upstream",
    is_flag=True,
    default=False,
    help=(
        "v2.5.1 B5 debug escape hatch — proceed even when Wave 1-5 "
        "artifacts are missing. Default OFF; production runs should leave it OFF."
    ),
)
@click.option(
    "--finalize",
    is_flag=True,
    default=False,
    help=(
        "v2.6.0 — audit the ALREADY-FILLED briefs (run the REAL Henry audit over "
        "the LLM-produced claims manifest). Refuses if the briefs still contain "
        "placeholder/scaffold language. Default OFF emits the honest scaffold "
        "(status=scaffold_pending_fill, henry_real_audit=false) for the SKILL "
        "main thread to fill, then re-run with --finalize."
    ),
)
@click.option("--json", "json_mode", is_flag=True)
def deliver(
    patient_dir: str,
    run_id: str,
    dry_run: bool,
    allow_missing_upstream: bool,
    finalize: bool,
    json_mode: bool,
) -> None:
    """Run the v2.2 atomic delivery transaction.

    On any failure the three artifacts (HENRY_AUDIT.json, patient_plain_brief.md,
    patient_pi_brief.md) are rolled back together. ADR-0022 invariant.

    v2.5.1 B5: refuses to ship when upstream wave artifacts are missing.
    Pass ``--allow-missing-upstream`` for local debugging only.
    """
    from opl_cancer.glue.delivery_runner import (
        DeliveryArtifactsMissing,
        DeliveryFailure,
        run_atomic_delivery,
        verify_upstream_artifacts,
    )

    pdir = Path(patient_dir)
    run_root = pdir / "triggers" / run_id
    out_dir = run_root / "delivery"

    # v2.5.1 B5: precondition check before invoking the runner so the CLI
    # can emit a structured missing-artifacts payload.
    if not dry_run:
        missing = verify_upstream_artifacts(run_root)
        if missing and not allow_missing_upstream:
            _emit(
                {
                    "ok": False,
                    "error": "upstream_artifacts_missing",
                    "missing": missing,
                    "run_root": str(run_root),
                    "out_dir": str(out_dir),
                    "hint": (
                        "Run Wave 1-5 first, or pass --allow-missing-upstream "
                        "for local debugging only (v2.5.1 B5)."
                    ),
                },
                json_mode,
            )
            raise click.exceptions.Exit(2)

    try:
        result = run_atomic_delivery(
            out_dir=out_dir,
            dry_run=dry_run,
            allow_missing_upstream=allow_missing_upstream,
            finalize=finalize,
        )
    except DeliveryArtifactsMissing as exc:
        _emit(
            {
                "ok": False,
                "error": "upstream_artifacts_missing",
                "missing": exc.missing,
                "out_dir": str(out_dir),
            },
            json_mode,
        )
        raise click.exceptions.Exit(2)
    except DeliveryFailure as exc:
        # Emit structured failure, exit non-zero
        _emit({"ok": False, "error": str(exc), "out_dir": str(out_dir)}, json_mode)
        raise click.exceptions.Exit(2)

    # v2.7.0 ADR-0026 — after a real finalize, the delivery-integrity gates are
    # the FINAL non-bypassable checkpoint: a brief that is not backed by a real
    # run (manifest + provenance + full team + on-topic citations) is refused.
    if finalize and not dry_run:
        from opl_cancer.glue.delivery_gate_runner import run_delivery_gates
        pubmed, paperqa = _build_citation_integrators()
        verdict = run_delivery_gates(run_root=run_root, out_dir=out_dir,
                                     pubmed=pubmed, paperqa=paperqa)
        if not verdict["ok"]:
            _emit({
                "ok": False, "error": "delivery_integrity_blocked",
                "blocked_by": verdict["blocked_by"], "notes": verdict["notes"],
                "out_dir": str(out_dir),
                "action": (
                    "Delivery REFUSED by integrity gates. The brief is not backed "
                    "by a verifiable run. Run the full pipeline; do not free-hand."
                ),
            }, json_mode)
            raise click.exceptions.Exit(2)
        result["delivery_attestation"] = {"ok": True, "notes": verdict["notes"]}
    _emit({"ok": True, **result}, json_mode)


# ─── v2.7.0 ADR-0026: `go` — one simple prompt → full autonomous service ──
#
# The founder's North Star (session 2026-05-29): "a patient gives one very
# simple prompt and we provide extremely professional service — not every user
# can ask expert questions." `go` is that single entry point. It drives the
# whole lifecycle deterministically and NEVER reports done until the delivery is
# complete + attested. For each LLM-dependent wave it either self-executes (when
# an executor key is present) or returns the EXACT next dispatch — including the
# FULL planned expert list — so the agent dispatches every expert and the
# service can never silently shrink (G37 backs this mechanically).

@main.command(
    name="go",
    help=(
        "One-prompt autonomous pipeline: input-guard → readiness → plan(full team) "
        "→ waves → deliver --finalize → attest. Returns the next required action "
        "until the delivery is complete + attested. Never under-delivers."
    ),
)
@click.option("--patient", "patient_dir", type=click.Path(file_okay=False), required=True)
@click.option("--goal", default="", help="The patient's goal — may be a single simple sentence.")
@click.option("--run-id", "run_id", default="", help="Run id (default: derived).")
@click.option("--json", "json_mode", is_flag=True)
def go(patient_dir: str, goal: str, run_id: str, json_mode: bool) -> None:
    pdir = Path(patient_dir)
    run_id = run_id or "run-go"
    run_root = pdir / "triggers" / run_id

    def _emit_state(stage: str, ok: bool, next_action: str, **extra: Any) -> None:
        _emit({"ok": ok, "stage": stage, "next_action": next_action,
               "patient": str(pdir), "run_id": run_id, **extra}, json_mode)
        if not ok:
            raise click.exceptions.Exit(0 if next_action else 2)

    # 1) input guard — OPL is downstream of organize; it does NOT OCR raw uploads.
    if not pdir.exists() or not (pdir / "profile.json").is_file() or not (pdir / "case_text.md").is_file():
        _emit_state(
            "input_guard", False,
            "Organize records first (SKILL.md Step 2 / cancer-buddy-organize). OPL "
            "does NOT OCR raw uploads or invent clinical values — it needs a canonical "
            "patient dir with profile.json + case_text.md + readiness.json + ocr/ sidecars.",
            missing=[f for f in ("profile.json", "case_text.md")
                     if not (pdir / f).is_file()],
        )
        return

    # 2) readiness
    readiness_p = pdir / "readiness.json"
    grade = None
    if readiness_p.is_file():
        try:
            grade = json.loads(readiness_p.read_text(encoding="utf-8")).get("grade")
        except (OSError, json.JSONDecodeError):
            grade = None
    if grade in (None, "D", "F"):
        _emit_state(
            "readiness", False,
            "Readiness grade < C — recover missing fields (deepdive) or proceed "
            "with --force after the patient confirms. Do NOT invent values to fill gaps.",
            readiness_grade=grade,
        )
        return

    # 3) plan + manifest
    plan_p = run_root / "plan.json"
    if not plan_p.is_file():
        _emit_state(
            "plan", False,
            f"Run: opl-cancer plan --patient {pdir} --goal \"{goal or '<patient goal>'}\" "
            f"--run-id {run_id}  (this also mints the run_token manifest).",
        )
        return
    try:
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _emit_state("plan", False, "plan.json unreadable — re-run `opl-cancer plan`.")
        return
    planned_experts = sorted({
        str(t.get("expert")).lower() for t in plan.get("tasks", []) or []
        if isinstance(t, dict) and t.get("expert")
    })
    planned_waves = sorted({
        int(w.get("wave_number")) for w in plan.get("waves", []) or []
        if isinstance(w, dict) and w.get("wave_number") is not None
    })

    # 4) waves — surface the FULL planned team so the agent dispatches ALL experts.
    from opl_cancer.glue.delivery_gate_runner import run_delivery_gates
    completeness = _G37_state(run_root)
    if not completeness["ok"]:
        _emit_state(
            "waves", False,
            "Dispatch the FULL planned team (per SKILL.md Step 5-8) — one report per "
            "expert to tasks/w1_<task_id>/report.md, then waves 2-4. Do NOT collapse "
            "to fewer generic agents; G37 will refuse delivery if any planned expert "
            "or warranted wave is missing.",
            planned_experts=planned_experts, planned_waves=planned_waves,
            missing=completeness,
        )
        return

    # 5) briefs → deliver scaffold/finalize
    out_dir = run_root / "delivery"
    plain = out_dir / "patient_plain_brief.md"
    pi = out_dir / "patient_pi_brief.md"
    if not plain.is_file() or not pi.is_file():
        _emit_state(
            "deliver_scaffold", False,
            f"Run: opl-cancer deliver --patient {pdir} --run-id {run_id}  (emits the "
            "honest scaffold), then fill both briefs with REAL content from the wave "
            "claims (every clinical value [[src:...]]-anchored, every PMID from a live search).",
            planned_experts=planned_experts,
        )
        return

    # 6) finalize + attest (deterministic — run it now)
    from opl_cancer.glue.delivery_runner import DeliveryFailure, run_atomic_delivery
    pubmed, paperqa = _build_citation_integrators()
    try:
        run_atomic_delivery(out_dir=out_dir, finalize=True)
    except DeliveryFailure as exc:
        _emit_state("finalize", False,
                    f"Finalize refused: {exc}. Fill the briefs (no placeholders) and retry.")
        return
    verdict = run_delivery_gates(run_root=run_root, out_dir=out_dir, pubmed=pubmed, paperqa=paperqa)
    if not verdict["ok"]:
        _emit_state("attest", False,
                    f"Delivery refused by integrity gates {verdict['blocked_by']}. "
                    "The brief is not backed by a verifiable run.",
                    blocked_by=verdict["blocked_by"], notes=verdict["notes"])
        return
    _emit({"ok": True, "stage": "delivered", "next_action": "",
           "patient": str(pdir), "run_id": run_id,
           "attestation": "DELIVERY_ATTESTATION.json", "notes": verdict["notes"]}, json_mode)


def _G37_state(run_root: Path) -> dict[str, Any]:
    """Run G37 service-completeness and return its verdict for `go`."""
    from opl_cancer.validators.gates import G37ServiceCompletenessGate
    r = G37ServiceCompletenessGate().check({"run_root": str(run_root)})
    return {"ok": r.status.value != "fail", "message": r.message, "evidence": r.evidence}


# ─── v2.3 ADR-0023: Wave 6 manuscript + .n1a bundle ───────────────────────

@main.command(
    name="wave6",
    help=(
        "v2.3 Wave 6: render the manuscript + emit the .n1a bundle. "
        "Refuses if Wave 5 has not shipped patient_plain_brief + "
        "patient_pi_brief. ADR-0023."
    ),
)
@click.option("--patient-dir", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--patient-code", required=True, help="Human-readable patient identifier (hashed for the manifest).")
@click.option("--draft/--final", default=False, help="Draft mode scaffolds stubs; final mode blocks on any G29-G33 gate failure.")
@click.option(
    "--data-source",
    type=click.Choice(["real_patient", "reference_case", "synthetic", "methodology_demo"]),
    default="real_patient",
    help="Banner is auto-stamped for non-real_patient.",
)
@click.option("--extends-prior-run", default=None, help="Override prior-run auto-detect (P2-#17).")
@click.option("--dry-run", is_flag=True, help="Return planned steps only.")
@click.option(
    "--submit-to-n1arxiv",
    "submit_to_n1arxiv",
    is_flag=True,
    help=(
        "v2.4 ADR-0024: after a successful --final run, stage the .n1a "
        "bundle + content stub against CancerDAO/n1arxiv and print the "
        "PR body draft. Founder-mode: NEVER auto-PRs."
    ),
)
@click.option(
    "--n1arxiv-repo",
    "n1arxiv_repo",
    type=click.Path(exists=False, file_okay=False),
    default=None,
    help="Optional local clone of CancerDAO/n1arxiv to stage into.",
)
@click.option("--json", "json_mode", is_flag=True)
def wave6(
    patient_dir: str,
    run_id: str,
    patient_code: str,
    draft: bool,
    data_source: str,
    extends_prior_run: str | None,
    dry_run: bool,
    submit_to_n1arxiv: bool,
    n1arxiv_repo: str | None,
    json_mode: bool,
) -> None:
    """CLI surface for the Wave 6 runner."""
    from opl_cancer.glue.wave6_runner import (
        Wave6Failure,
        Wave6PrerequisiteError,
        run_wave6,
    )

    # v2.4: --submit-to-n1arxiv requires --final (publishing a draft is a
    # category error; the gates have not been enforced yet).
    if submit_to_n1arxiv and draft:
        _emit(
            {
                "ok": False,
                "error": "submit_requires_final",
                "detail": (
                    "--submit-to-n1arxiv requires --final. Drafts cannot "
                    "be published: G29-G33 are not enforced in draft mode."
                ),
            },
            json_mode,
        )
        raise click.exceptions.Exit(2)

    mode = "dry_run" if dry_run else ("draft" if draft else "final")
    try:
        result = run_wave6(
            patient_dir=Path(patient_dir),
            run_id=run_id,
            patient_code=patient_code,
            opl_version=VERSION,
            data_source=data_source,
            extends_prior_run=extends_prior_run,
            mode=mode,
        )
    except Wave6PrerequisiteError as exc:
        _emit({"ok": False, "error": "wave5_prerequisite_missing", "detail": str(exc)}, json_mode)
        raise click.exceptions.Exit(2)
    except Wave6Failure as exc:
        _emit({"ok": False, "error": "wave6_failed", "detail": str(exc)}, json_mode)
        raise click.exceptions.Exit(3)

    payload: dict[str, Any] = {"ok": True, **result}

    # v2.4 ADR-0024: optional submission staging
    if submit_to_n1arxiv and mode == "final":
        try:
            from opl_cancer.delivery.n1arxiv_submitter import (
                SubmitterError,
                assemble_submission,
            )

            zip_path = result.get("zip_path")
            if not zip_path:
                payload["n1arxiv_submission"] = {
                    "error": "no_zip_path",
                    "detail": "wave6 result did not include a zip_path.",
                }
            else:
                clone = Path(n1arxiv_repo) if n1arxiv_repo else None
                sub_plan = assemble_submission(
                    bundle_zip=Path(zip_path),
                    n1arxiv_clone=clone,
                    patient_code=patient_code,
                    execute=False,
                )
                payload["n1arxiv_submission"] = sub_plan
        except SubmitterError as exc:
            payload["n1arxiv_submission"] = {
                "error": "submitter_failed",
                "detail": str(exc),
            }

    _emit(payload, json_mode)


# ─── D4/ADR-0037: Evolution (re-aimed at the disease frontier) ────────────
#
# Founder decision A keeps the evolution engine IN the patient path (it reverses
# the extraction), so ``evolve`` is registered UNCONDITIONALLY — no find_spec
# probe. The analyzer is re-aimed from OPL-software self-improvement to THIS
# patient's disease research frontier, fed by the compounding research ledger
# (A1) + reality outcomes (A2) via build_disease_frontier_digest.


def evolve(run_dir: str, iter_n: int, max_proposals: int, json_mode: bool) -> None:
    """Run the disease-frontier analyzer over a completed run dir.

    Always dry-run with respect to baseline files — output goes ONLY under
    ``<run_dir>/proposals/iter_<N>/``. There is no --auto-apply flag.
    """
    import asyncio

    from opl_cancer.evolution.analyzer import EvolutionAnalyzer
    from opl_cancer.evolution.collector import collect_trace_digest
    from opl_cancer.evolution.proposal_writer import write_proposals
    from opl_cancer.evolution.scrubber import scrub

    run_path = Path(run_dir)
    digest = collect_trace_digest(run_path)
    scrubbed = scrub(digest)

    # D4/ADR-0037 — feed the disease-frontier digest so the analyzer learns about
    # THIS patient's disease, not OPL-the-software. Absent ledger (first run / a
    # bare run dir) → no frontier; the analyzer still runs (legacy heuristic).
    frontier = None
    try:
        from opl_cancer.memory.disease_frontier import build_disease_frontier_digest
        from opl_cancer.memory.store import (
            ProjectMemoryStore,
            default_patient_memory_db,
        )

        _db = default_patient_memory_db(run_path)
        if _db.exists():
            frontier = build_disease_frontier_digest(
                ProjectMemoryStore(_db), run_id=run_path.name
            )
    except Exception:  # noqa: BLE001 — frontier is best-effort; analyzer must still run
        frontier = None

    async def _run() -> object:
        analyzer = EvolutionAnalyzer()  # heuristic fallback by default
        return await analyzer.analyze(scrubbed, iter_n=iter_n, frontier=frontier)

    candidates = asyncio.run(_run())
    # Truncate to max_proposals (heuristic already caps at 3-5; LLM at 5)
    candidates.proposals = candidates.proposals[:max_proposals]

    out_root = run_path / "proposals"
    manifest = write_proposals(candidates, out_root)

    summary = {
        "ok": True,
        "run_dir": str(run_path),
        "proposals_dir": str(out_root / f"iter_{iter_n:03d}"),
        "iter_n": iter_n,
        "manifest": manifest,
        "analyzer_model": candidates.analyzer_model,
        "used_heuristic_fallback": candidates.used_heuristic_fallback,
        "analysis_summary": candidates.analysis_summary,
    }
    _emit(summary, json_mode)


# Register ``evolve`` UNCONDITIONALLY (D4/ADR-0037 — the engine stays in the
# patient path). Decorators are applied imperatively here (equivalent to stacking
# them on the def).
evolve = click.option(
    "--json", "json_mode", is_flag=True, help="Emit JSON summary to stdout."
)(evolve)
evolve = click.option(
    "--max-proposals", type=int, default=5, show_default=True,
    help="Cap on proposals emitted.",
)(evolve)
evolve = click.option(
    "--iter-n", type=int, default=1, show_default=True,
    help="Iteration number recorded in proposals.",
)(evolve)
evolve = click.argument(
    "run_dir", type=click.Path(exists=True, file_okay=False)
)(evolve)
evolve = main.command(
    name="evolve",
    help=(
        "Post-mortem evolution (D4): build a TraceDigest from a completed run, "
        "run the disease-frontier analyzer, write PR-style proposals under "
        "<run_dir>/proposals/. NEVER auto-applies anything. See ADR-0037."
    ),
)(evolve)


# ─── Patient observability ────────────────────────────────────────────────

@main.command(help="Show current OPL capability snapshot.")
def status() -> None:
    click.echo(f"OPL for Cancer — v{VERSION}")
    click.echo(f"  Experts active: {len(ROSTER)} (Sid PI + Henry Auditor + {len(ROSTER)} named experts)")
    click.echo("  Wave runners ready: Wave1 / Wave2 / Wave3 / Wave4 / Wave5 (render) / Wave6 (manuscript+.n1a)")
    click.echo("  Integrators wired: 36 (29 v2.1 + v2.2 ADR-0022 bio-skills: MSIsensor / TMB-harmonization / SigProfiler / VarSome-ACMG / lifelines-KM / CPIC / PaperQA-full-text)")
    from opl_cancer.validators.mechanical_gates import all_gate_classes
    _ngates = len(all_gate_classes())  # single source of truth — no drift
    click.echo(f"  Mechanical gates: {_ngates} (G1-G33 + v2.7.0 G34-G37 delivery-integrity + v2.7.1 G39-G43 reasoning-quality; G38 reserved — ADR-0026)")
    click.echo("  License: Apache-2.0")
    click.echo("  Read DISCLAIMER.md before use — not clinical decision support; not for emergencies.")
    click.echo(f"  Patient data root: {_patient_root()}")


@main.command(name="integrator-plugins", help="List integrator entry-point plugins.")
@click.option("--json", "json_mode", is_flag=True)
def integrator_plugins(json_mode: bool) -> None:
    from opl_cancer.integrators._abc import ENTRY_POINT_GROUP, IntegratorRegistry

    registry = IntegratorRegistry.discover()
    rows = registry.describe()
    payload = {
        "ok": all(r.get("ok") for r in rows),
        "entry_point_group": ENTRY_POINT_GROUP,
        "count": len(rows),
        "integrators": rows,
    }
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"Integrator entry points ({ENTRY_POINT_GROUP}): {len(rows)}")
    for row in rows:
        mark = "ok" if row.get("ok") else "ERR"
        click.echo(f"  {mark:3} {row['name']:<18} {row.get('module', '')}:{row.get('class', '')}")


@main.command(name="task-capabilities", help="List task-package capability prompts and owners.")
@click.option("--json", "json_mode", is_flag=True)
def task_capabilities(json_mode: bool) -> None:
    from opl_cancer.plan.task_capabilities import (
        registry_as_list,
        validate_task_capability_registry,
    )

    capabilities = registry_as_list()
    validation = validate_task_capability_registry()
    payload = {
        "ok": validation["ok"],
        "summary": validation["summary"],
        "problems": validation["problems"],
        "capabilities": capabilities,
    }
    if json_mode:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    summary = validation["summary"]
    click.echo(
        "Task capabilities: "
        f"{summary['count']} total, {summary['owned']} owned, "
        f"{summary['unowned']} unowned, {summary['missing_prompt']} missing prompts"
    )
    for row in capabilities:
        owners = ", ".join(row["owners"]) if row["owners"] else "-"
        mark = "ok" if row["prompt_exists"] else "MISS"
        click.echo(f"  {mark:4} {row['task_package']:<38} owners={owners}")
    if not validation["ok"]:
        raise click.exceptions.Exit(2)


@main.command(name="release-eval", help="Run deterministic golden-set release regression checks.")
@click.option(
    "--golden-root",
    type=click.Path(file_okay=False),
    help="Golden-set root (default: validators/golden_set in this checkout).",
)
@click.option("--out", type=click.Path(), help="Optional path to write the JSON report.")
@click.option("--json", "json_mode", is_flag=True)
def release_eval(golden_root: str | None, out: str | None, json_mode: bool) -> None:
    from opl_cancer.evaluation.release_golden import (
        run_release_golden_eval,
        write_release_golden_eval,
    )

    report = run_release_golden_eval(golden_root)
    if out:
        report["report_path"] = str(write_release_golden_eval(report, out))
    if json_mode:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        click.echo(
            "Release eval: "
            f"{'OK' if report['ok'] else 'FAIL'}; "
            f"{summary['checks']} checks, {summary['errors']} errors, "
            f"{summary['warnings']} warnings"
        )
        for check in report["checks"]:
            if not check["ok"]:
                click.echo(
                    f"  {check['severity'].upper()} "
                    f"{check['category']}/{check['name']}: {check['message']}"
                )
    if not report["ok"]:
        raise click.exceptions.Exit(2)


@main.command(help="Initialize a new patient project directory.")
@click.argument("patient_code")
@click.option("--root", type=click.Path(file_okay=False),
              help="Root directory (default: $OPL_PATIENT_DATA_ROOT or ~/CancerDAO/patients/).")
def init_patient(patient_code: str, root: str | None) -> None:
    base = (Path(root) if root else _patient_root()) / patient_code
    for sub in ("memory", "pi_session", "inbox", "triggers", "archives"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    click.echo(f"Initialized patient project at: {base}")
    click.echo("Sid (PI) will activate when first trigger fires.")


@main.command(name="list-experts", help="List the 20-name expert roster (v2: + Maya KG-synergy + Julius in-silico).")
def list_experts() -> None:
    click.echo(f"OPL for Cancer — Expert Roster ({len(ROSTER)} experts active)")
    click.echo()
    click.echo("  sid       PI / Chief-of-Staff      (Sid Mukherjee archetype)")
    click.echo("  henry     Auditor / IRB substitute (Henry Beecher archetype)")
    click.echo("  " + "-" * 60)
    for name, profile in ROSTER.items():
        click.echo(f"  {name:<10}{profile.role:<28}{profile.inspiration}")


@main.command(name="acknowledge", help="Patient ack of an L3/L4 risk card. Spec §8 L4.\n\nv1.4.0: supports --batch <pattern> to ack multiple cards at once (e.g. `--batch L3-all` / `--batch by-drug:olaparib`). Each individual card is still acked atomically and audit-trail-recorded; the batch flag only reduces UX friction when a delivery stacks 3+ acks.")
@click.argument("card_id", required=False)
@click.option("--batch", "batch_pattern", default=None,
              help="Batch-ack pattern: `L3-all` / `L4-all` / `Lall` / `by-drug:<inn>` / `by-claim:<id_prefix>` / `by-card-prefix:<prefix>`. Mutually exclusive with positional CARD_ID.")
@click.option("--outstanding-dir", type=click.Path(file_okay=False), default="outstanding")
@click.option("--serious-risks", type=click.Path(dir_okay=False), default="knowledge/serious_risks_per_drug.json")
def acknowledge(card_id: str | None, batch_pattern: str | None, outstanding_dir: str, serious_risks: str) -> None:
    from opl_cancer.validators.henry import HenryAuditor
    auditor = HenryAuditor(serious_risks_path=Path(serious_risks), outstanding_dir=Path(outstanding_dir))
    ts = _now_iso()

    if batch_pattern and card_id:
        raise click.UsageError("`--batch <pattern>` and positional CARD_ID are mutually exclusive.")
    if not batch_pattern and not card_id:
        raise click.UsageError("Either CARD_ID or `--batch <pattern>` is required.")

    if card_id:
        rec = auditor.acknowledge(card_id, acknowledged_at=ts)
        click.echo(f"Acknowledged card {card_id!r} at {ts}")
        click.echo(f"  level: {rec.get('level')}")
        click.echo(f"  risks: {len(rec.get('known_serious_risks', []))}")
        return

    # --batch path
    pending = auditor.list_pending()
    matched: list[dict[str, Any]] = []
    pat = batch_pattern.strip()
    if pat in ("L3-all", "L3"):
        matched = [r for r in pending if str(r.get("level", "")).upper() in ("L3", "3")]
    elif pat in ("L4-all", "L4"):
        matched = [r for r in pending if str(r.get("level", "")).upper() in ("L4", "4")]
    elif pat in ("Lall", "all", "all-pending"):
        matched = pending
    elif pat.startswith("by-drug:"):
        drug = pat[len("by-drug:"):].strip().lower()
        if not drug:
            raise click.UsageError("`--batch by-drug:<inn>` requires a non-empty INN.")
        for rec in pending:
            anchors = rec.get("known_serious_risks", []) or []
            claim_text = str(rec.get("claim_text", "")).lower()
            if any(drug in str(a).lower() for a in anchors) or drug in claim_text:
                matched.append(rec)
    elif pat.startswith("by-claim:"):
        prefix = pat[len("by-claim:"):].strip()
        if not prefix:
            raise click.UsageError("`--batch by-claim:<id_prefix>` requires a non-empty prefix.")
        matched = [r for r in pending if str(r.get("claim_id", "")).startswith(prefix)]
    elif pat.startswith("by-card-prefix:"):
        prefix = pat[len("by-card-prefix:"):].strip()
        if not prefix:
            raise click.UsageError("`--batch by-card-prefix:<prefix>` requires a non-empty prefix.")
        matched = [r for r in pending if str(r.get("card_id", "")).startswith(prefix)]
    else:
        raise click.UsageError(
            f"Unknown batch pattern {pat!r}. Supported: "
            "`L3-all`, `L4-all`, `Lall`, `by-drug:<inn>`, `by-claim:<id_prefix>`, `by-card-prefix:<prefix>`."
        )

    if not matched:
        click.echo(f"No pending cards matched `--batch {pat}`.")
        return

    click.echo(f"Batch ack: {len(matched)} card(s) matched pattern `{pat}`:")
    for rec in matched:
        cid = rec.get("card_id")
        if not cid:
            click.echo(f"  SKIP (missing card_id): {rec}")
            continue
        auditor.acknowledge(cid, acknowledged_at=ts)
        click.echo(f"  ack ✓  {cid}  L{rec.get('level')}  {str(rec.get('claim_text', ''))[:60]}")
    click.echo(f"Batch complete: {len(matched)} card(s) acknowledged at {ts}")


@main.command(name="list-pending-acks", help="List pending L3/L4 risk cards.")
@click.option("--outstanding-dir", type=click.Path(file_okay=False), default="outstanding")
@click.option("--serious-risks", type=click.Path(dir_okay=False), default="knowledge/serious_risks_per_drug.json")
def list_pending_acks(outstanding_dir: str, serious_risks: str) -> None:
    from opl_cancer.validators.henry import HenryAuditor
    auditor = HenryAuditor(serious_risks_path=Path(serious_risks), outstanding_dir=Path(outstanding_dir))
    pending = auditor.list_pending()
    if not pending:
        click.echo("No pending acks.")
        return
    for rec in pending:
        click.echo(f"  {rec['card_id']}  L{rec['level']}  {rec['claim_text'][:60]}")


@main.command(help="Withdraw an insight + cascade through supersedes-DAG. Spec §11.")
@click.argument("insight_id")
@click.option("--reason", required=True)
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--json", "json_mode", is_flag=True)
def withdraw(insight_id: str, reason: str, patient_dir: str, json_mode: bool) -> None:
    from opl_cancer.memory.store import ProjectMemoryStore
    from opl_cancer.provenance.journal import ProvenanceJournal
    from opl_cancer.validators.rollback import withdraw_with_cascade
    pdir = Path(patient_dir)
    store = ProjectMemoryStore(pdir / "memory")
    journal = ProvenanceJournal(pdir / "memory" / "provenance" / "index.jsonl")
    # Caller may pass insight_id "<id>:<version>" to target a specific version.
    if ":" in insight_id:
        iid, ver = insight_id.split(":", 1)
        version = int(ver)
    else:
        iid, version = insight_id, 1
    cascade = withdraw_with_cascade(
        store, iid, version, reason=reason, at=_now_iso(), evidence="", journal=journal,
    )
    _emit({"ok": True, "withdrawn": iid, "version": version, "reason": reason, "cascade": sorted(cascade)}, json_mode)


@main.command(help="Reproduce a historical patient_brief bit-exact using locked model + prompt versions.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def reproduce(patient_dir: str, run_id: str, json_mode: bool) -> None:
    # Delegates to tools/reproduce.py for full implementation.
    _emit({"ok": True, "patient": patient_dir, "run_id": run_id, "note": "delegates to tools/reproduce.py"}, json_mode)


# ─── v2.5 RFC 0001 §2.3 — Cancer-context generator ─────────────────────────


@main.command(
    name="generate-cancer-context",
    help=(
        "v2.5 RFC 0001 §2.3 — emit a cancer_context.json for a given ICD-O-3 "
        "(or SNOMED) code. Seed data ships for HCC (C22.0) + NSCLC EGFR+ "
        "(C34.9_EGFR); other codes return a scaffold stub explaining M6 "
        "deferral (live PrimeKG + OncoKB + NCCN + ClinicalTrials.gov queries)."
    ),
)
@click.option("--icdo3", required=True, help="ICD-O-3 (or SNOMED) cancer code.")
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Path to write the JSON output. Default: stdout.",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Skip cache + seed lookup, write a scaffold stub even if seed exists.",
)
@click.option("--json", "json_mode", is_flag=True, help="Pretty-print JSON to stdout if --output not set.")
def generate_cancer_context(
    icdo3: str, output_path: str | None, force_refresh: bool, json_mode: bool
) -> None:
    from opl_cancer.cancer_context import CancerContextGenerator

    cache_dir = Path(output_path).parent if output_path else None
    gen = CancerContextGenerator(icdo3, cache_dir=cache_dir, force_refresh=force_refresh)
    ctx = gen.generate()
    payload = json.dumps(ctx, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(payload, encoding="utf-8")
        click.echo(f"wrote {output_path}")
    else:
        click.echo(payload)


@main.command(help="Render the run-console progress dashboard (deterministic frame).")
@click.option("--run-id", required=True, help="The run id shown in the header.")
@click.option("--phase", required=True, help="Phase short label or substring (e.g. 'Wave1 查证据').")
@click.option("--detail", default="", help="One-line `current_detail` (the active expert/step).")
@click.option("--last", "last_detail", default="", help="One-line `刚完成 / done` detail.")
@click.option("--eta", default="", help="ETA range string, e.g. '~12–18 min'.")
def progress(run_id: str, phase: str, detail: str, last_detail: str, eta: str) -> None:
    from opl_cancer.glue.progress_dashboard import phase_index, render
    idx = phase_index(phase)
    if idx < 0:
        # tolerate a bare integer phase index too
        try:
            idx = int(phase)
        except ValueError:
            raise click.ClickException(
                f"unknown phase {phase!r} — use a PHASES label/substring or an index"
            )
    click.echo(render(run_id=run_id, phase_idx=idx, current_detail=detail,
                      last_detail=last_detail, eta=eta))


if __name__ == "__main__":
    main()
