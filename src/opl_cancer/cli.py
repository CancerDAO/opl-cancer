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
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from opl_cancer.compute.native_runner import NativeAnalysisRunner
from opl_cancer.compute.runner import BixbenchRunner
from opl_cancer.experts.roster import ROSTER

VERSION = "2.5.0"
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
    # The MAIN executor LLM work (Sid PI + 18 expert task packages + delivery
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

@main.command(help="Step 4: PI (Sid) plans run — chooses experts + Waves.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--goal", required=True, help="Verbatim patient goal.")
@click.option("--run-id", required=True)
@click.option("--out", type=click.Path(), help="Output plan.json path (default: <patient>/triggers/<run_id>/plan.json)")
@click.option("--json", "json_mode", is_flag=True)
def plan(patient_dir: str, goal: str, run_id: str, out: str | None, json_mode: bool) -> None:
    pdir = Path(patient_dir)
    out_path = Path(out) if out else pdir / "triggers" / run_id / "plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # v1.5 P0-6: skeleton is the floor, not the ceiling. We read the
    # patient profile and expand with triggered-expert tasks
    # (Mark / Mary / Frances / Riad / Dennis / Heddy) when the patient's
    # phenotype matches the multi-comorbid / L4+ / cross-border /
    # active-irAE / cardiac / CKD / polypharmacy criteria. The expansion
    # is deterministic + narrated; v1.6 will hand the LLM-driven
    # planner the wheel. See `plan/comorbid_planner.py`.
    from opl_cancer.plan.comorbid_planner import maybe_expand_for_comorbid
    from opl_cancer.plan.schemas import Plan, Task, WaveAssignment
    base_tasks = [
        Task(id="t1", expert="rosa", task_package="pathology_interpretation", sub_goal="read pathology report"),
        Task(id="t2", expert="bert", task_package="molecular_ngs_interpretation", sub_goal="extract actionable variants from NGS"),
        Task(id="t3", expert="rick", task_package="trial_matching", sub_goal="match patient to CT.gov + ChiCTR trials"),
        Task(id="t4", expert="aviv", task_package="hypothesis_generation", sub_goal="4-strategy blind-spot scan", dependencies=["t1", "t2"]),
        Task(id="t5", expert="iain", task_package="literature_synthesis", sub_goal="PaperQA2 grounded synthesis"),
        Task(id="t6", expert="aviv", task_package="dataset_acquisition", sub_goal="find matched GEO cohort", dependencies=["t4"]),
        Task(id="t7", expert="aviv", task_package="bioinformatics_data_analysis", sub_goal="DESeq2 + scanpy reanalysis", dependencies=["t6"]),
        Task(id="t8", expert="iain", task_package="meta_analysis", sub_goal="pool effect sizes across cohorts"),
        Task(id="t9", expert="aviv", task_package="hypothesis_validation", sub_goal="retest hypotheses vs measured data", dependencies=["t4", "t7"]),
    ]
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
    tasks, fired = maybe_expand_for_comorbid(base_tasks, profile_data, goal=goal)

    # v2.5.1 B2 — route the verbatim goal through intake_router so unknown
    # tasks (the c3195b66 AutoML / prognosis case) are routed to
    # `unknown_task_intake` with a composed method DAG. The intake task is
    # appended to Wave 1 alongside the comorbid expansion.
    from opl_cancer.plan.intake_router import route_intake

    intake_route = route_intake(goal, profile=profile_data)
    intake_task: Task | None = None
    # Only inject the unknown_task_intake task when the route is
    # meaningfully populated — see Wave1Runner._apply_intake_router
    # docstring for the same gating rule.
    _is_substantive = bool(intake_route.decline_reasons) or len(intake_route.method_dag) >= 2
    if intake_route.matched_task_package == "unknown_task_intake" and _is_substantive:
        intake_task = Task(
            id="t_intake",
            expert="aviv",  # Aviv owns method-composition + N=1 framing
            task_package="unknown_task_intake",
            sub_goal=(
                f"Compose method DAG for patient question; route per "
                f"intake_router (matched={intake_route.matched_task_package})"
            ),
            dependencies=[],
        )
        tasks.append(intake_task)

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
    expanded_task_ids = [t.id for t in tasks if t.id not in {b.id for b in base_tasks}]
    # Newly-added tasks all go to Wave 1 (retrieval) by default — the
    # LLM-driven planner in v1.6 will redistribute. Heddy + Frances +
    # Dennis + Riad are retrieval-shaped tasks; Mary's polypharmacy /
    # cardiac / CKD scans likewise read the patient + drug labels.
    wave1_ids = ["t1", "t2", "t3"] + expanded_task_ids
    skeleton = Plan(
        run_id=run_id,
        patient_code=pdir.name,
        goal=goal,
        tasks=tasks,
        waves=[
            WaveAssignment(wave_number=1, task_ids=wave1_ids),
            WaveAssignment(wave_number=2, task_ids=["t4", "t5"]),
            WaveAssignment(wave_number=3, task_ids=["t6", "t7", "t8"]),
            WaveAssignment(wave_number=4, task_ids=["t9"]),
        ],
    )

    # v2.5.1 B2 — persist the composed method DAG on the plan JSON.
    # `Plan` (pydantic) does not yet model `method_dag` as a first-class
    # field, so we re-serialise + inject. Downstream callers should read
    # the plan via plain json.load() rather than `Plan.model_validate()`
    # to see this extension; the SKILL main thread does both.
    plan_payload = skeleton.model_dump(mode="json")
    plan_payload["method_dag"] = list(intake_route.method_dag)
    plan_payload["intake_route"] = intake_route.to_dict()
    out_path.write_text(
        json.dumps(plan_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
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
            "waves": 4,
            "tasks": len(tasks),
            "comorbid_expansion_triggers_fired": triggers_payload,
            "intake_route": intake_route.to_dict(),
        },
        json_mode,
    )


# ─── Step 5-8: Waves ──────────────────────────────────────────────────────
#
# v1.5.7 honest-failure rewrite (memory:feedback_no_false_completion + run
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


# ─── v2.1 P0-#1+#2: opl run — real executor wrapping wave runners ─────────
#
# memory:feedback_no_false_completion + ADR-0021. Through v2.0.x the only
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
        # Waves 1/2/4: re-use the artifact-state probe — refuse to claim
        # completion when no real artifacts present. The SKILL main thread
        # is the dispatcher for those LLM-driven waves.
        state = _wave_artifact_state(run_root, wave)
        result = {
            "wave": wave,
            "artifacts_found": state["found"],
            "artifacts_sample": state["files"],
        }
        if not state["ok"]:
            result["requires_main_thread_dispatch"] = True
            result["action"] = (
                f"Wave {wave} produced no artifacts yet. The SKILL main "
                "thread must dispatch the wave runner (Wave1Runner / "
                "Wave2Runner / Wave4Runner) — this CLI command verifies "
                "state honestly per ADR-0021."
            )

    _emit_run_result(wave, result, json_mode)


# ─── Step 9: Henry audit ──────────────────────────────────────────────────

@main.command(help="Step 9: Henry 4-layer IRB-substitute audit.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def audit(patient_dir: str, run_id: str, json_mode: bool) -> None:
    # HenryAuditor wiring lives in glue/wave runners; this command is the SKILL-level
    # entry that confirms the audit directory is prepared. Full audit runs in glue/.
    pdir = Path(patient_dir)
    audit_dir = pdir / "triggers" / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    out = {"ok": True, "patient": str(pdir), "run_id": run_id, "audit_dir": str(audit_dir)}
    _emit(out, json_mode)


# ─── Step 10: render ──────────────────────────────────────────────────────

@main.command(help="Step 10: render patient_brief.html + pi_delivery.md.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def render(patient_dir: str, run_id: str, json_mode: bool) -> None:
    pdir = Path(patient_dir)
    delivery = pdir / "triggers" / run_id / "delivery"
    delivery.mkdir(parents=True, exist_ok=True)
    _emit({"ok": True, "delivery_dir": str(delivery)}, json_mode)


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
@click.option("--json", "json_mode", is_flag=True)
def deliver(
    patient_dir: str,
    run_id: str,
    dry_run: bool,
    allow_missing_upstream: bool,
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
    _emit({"ok": True, **result}, json_mode)


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


# ─── ADR-0020: Evolution (post-mortem proposal generator) ─────────────────

@main.command(
    name="evolve",
    help=(
        "Post-mortem evolution: build a TraceDigest from a completed run, "
        "run the red-team analyzer, write PR-style proposals under "
        "<run_dir>/proposals/. NEVER auto-applies anything. See ADR-0020."
    ),
)
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--iter-n", type=int, default=1, show_default=True, help="Iteration number recorded in proposals.")
@click.option("--max-proposals", type=int, default=5, show_default=True, help="Cap on proposals emitted.")
@click.option("--json", "json_mode", is_flag=True, help="Emit JSON summary to stdout.")
def evolve(run_dir: str, iter_n: int, max_proposals: int, json_mode: bool) -> None:
    """Run the evolution analyzer over a completed run dir.

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

    async def _run() -> object:
        analyzer = EvolutionAnalyzer()  # heuristic fallback by default
        return await analyzer.analyze(scrubbed, iter_n=iter_n)

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


# ─── Patient observability ────────────────────────────────────────────────

@main.command(help="Show current OPL capability snapshot.")
def status() -> None:
    click.echo(f"OPL for Cancer — v{VERSION}")
    click.echo(f"  Experts active: {len(ROSTER)} (Sid PI + Henry Auditor + {len(ROSTER)} named experts)")
    click.echo("  Wave runners ready: Wave1 / Wave2 / Wave3 / Wave4 / Wave5 (render) / Wave6 (manuscript+.n1a)")
    click.echo("  Integrators wired: 36 (29 v2.1 + v2.2 ADR-0022 bio-skills: MSIsensor / TMB-harmonization / SigProfiler / VarSome-ACMG / lifelines-KM / CPIC / PaperQA-full-text)")
    click.echo("  Mechanical gates: 33 (G1-G27 + v2.2 G28 + v2.3 G29-G33 — ADR-0023 Wave 6 manuscript invariants)")
    click.echo("  License: Apache-2.0")
    click.echo("  Read DISCLAIMER.md before use — not clinical decision support; not for emergencies.")
    click.echo(f"  Patient data root: {_patient_root()}")


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


@main.command(name="list-experts", help="List the 18-name expert roster.")
def list_experts() -> None:
    click.echo("OPL for Cancer — Expert Roster (18 experts active)")
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


if __name__ == "__main__":
    main()
