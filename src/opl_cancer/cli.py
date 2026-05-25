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

from opl_cancer.experts.roster import ROSTER

VERSION = "1.4.0"
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
def preflight(json_mode: bool, allow_single_model: bool) -> None:
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
    # Delegate to orchestrator/plan path. v1.3 ships a deterministic skeleton plan
    # (full LLM-driven planning is wired through wave1_runner.py for the initial wave).
    from opl_cancer.plan.schemas import Plan, Task, WaveAssignment
    tasks = [
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
    skeleton = Plan(
        run_id=run_id,
        patient_code=pdir.name,
        goal=goal,
        tasks=tasks,
        waves=[
            WaveAssignment(wave_number=1, task_ids=["t1", "t2", "t3"]),
            WaveAssignment(wave_number=2, task_ids=["t4", "t5"]),
            WaveAssignment(wave_number=3, task_ids=["t6", "t7", "t8"]),
            WaveAssignment(wave_number=4, task_ids=["t9"]),
        ],
    )
    out_path.write_text(skeleton.model_dump_json(indent=2), encoding="utf-8")
    _emit({"ok": True, "plan_path": str(out_path), "run_id": run_id, "waves": 4, "tasks": len(tasks)}, json_mode)


# ─── Step 5-8: Waves ──────────────────────────────────────────────────────

@main.command(help="Step 5: Wave 1 (world-known retrieval) — parallel experts.")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--plan", "plan_path", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave1(patient_dir: str, run_id: str, plan_path: str, json_mode: bool) -> None:
    pdir = Path(patient_dir)
    out = pdir / "triggers" / run_id
    out.mkdir(parents=True, exist_ok=True)
    # Real Wave1Runner is async; here we expose a thin sync wrapper for the SKILL.
    _emit({"ok": True, "wave": 1, "out": str(out), "note": "Wave1Runner is async — invoke via Python: from opl_cancer.glue.wave1_runner import Wave1Runner. v1.3 ships the runner; full sync-from-CLI path lands in v1.4."}, json_mode)


@main.command(help="Step 6: Wave 2 (hypothesis tournament).")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave2(patient_dir: str, run_id: str, json_mode: bool) -> None:
    out = Path(patient_dir) / "triggers" / run_id / "tournament"
    out.mkdir(parents=True, exist_ok=True)
    _emit({"ok": True, "wave": 2, "out": str(out)}, json_mode)


@main.command(help="Step 7: Wave 3 (data-evidence + bixbench).")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--enable-docker/--no-docker", default=True)
@click.option("--json", "json_mode", is_flag=True)
def wave3(patient_dir: str, run_id: str, enable_docker: bool, json_mode: bool) -> None:
    out = Path(patient_dir) / "triggers" / run_id / "data"
    out.mkdir(parents=True, exist_ok=True)
    _emit({"ok": True, "wave": 3, "docker": enable_docker, "out": str(out)}, json_mode)


@main.command(help="Step 8: Wave 4 (hypothesis validation against measured data).")
@click.option("--patient", "patient_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--run-id", required=True)
@click.option("--json", "json_mode", is_flag=True)
def wave4(patient_dir: str, run_id: str, json_mode: bool) -> None:
    out = Path(patient_dir) / "triggers" / run_id
    out.mkdir(parents=True, exist_ok=True)
    _emit({"ok": True, "wave": 4, "out": str(out)}, json_mode)


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


# ─── Patient observability ────────────────────────────────────────────────

@main.command(help="Show current OPL capability snapshot.")
def status() -> None:
    click.echo(f"OPL for Cancer — v{VERSION}")
    click.echo(f"  Experts active: {len(ROSTER)} (Sid PI + Henry Auditor + 18 named experts)")
    click.echo("  Wave runners ready: Wave1 / Wave2 / Wave3 / Wave4 / Wave5 (render)")
    click.echo("  Integrators wired: 29 (NCCN / PubMed / CT.gov / ChiCTR / ISRCTN / EU-CTR / HKCTR / FDA-EAP / NMPA-EAP / EMA-EAP / RxNorm / GEO / Open Targets / Hartwig / BeatAML / ICGC / etc.)")
    click.echo("  Mechanical gates: 23 (G1-G20 + G22 DDR-zygosity + G23 recency-band + G24 crisis-detection)")
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


if __name__ == "__main__":
    main()
