"""Wave 3 data-evidence pipeline. P3-T11.

Drives Aviv (+ optional Tyler) through:
    1. dataset_acquisition  — given patient + Wave-2 hypotheses, identify
       matching public datasets (GEO/ArrayExpress/SRA)
    2. bioinformatics_data_analysis — propose analysis plan + (dry-run)
       BixbenchRunner invocation
    3. hypothesis_validation — for each Wave-2 top-hypothesis, validate /
       falsify against data evidence (Tyler if provided, else Aviv)

Writes ``triggers/<run_id>/wave3_data_evidence.json`` + provenance.jsonl.
Per ADR-2026-04-22 — main-thread sequential awaits.
no-silent-fallback policy — no silent network fallback; integrators raise.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.compute.native_runner import NativeAnalysisRunner
from opl_cancer.compute.runner import BixbenchRunner
from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.glue._post_write import post_write_safety_check
from opl_cancer.glue.progress_reporter import ProgressReporter
from opl_cancer.integrators.paperqa_full_text import (
    classify_calibration_provenance,
)
# NOTE (harness-split): orchestrator.* is the self-improvement engine and is
# being extracted to a standalone repo. Import it lazily so this runner stays
# importable when orchestrator/ is absent; the symbol is only needed when a
# wave is actually executed. ``run_reviewer_pairing`` is still exposed as a
# module attribute via PEP 562 ``__getattr__`` (resolved on first access) so the
# B3 wiring contract (test_sniffer_halt_wave3) holds without a module-load
# dependency on orchestrator/.
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal


def __getattr__(name: str):  # PEP 562 — lazy orchestrator re-export
    if name == "run_reviewer_pairing":
        from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing
        return run_reviewer_pairing
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def record_monte_carlo_calibration(
    *,
    parameter_name: str,
    value: float,
    extracted_quote: str | None,
    was_from_full_text: bool,
    used_default: bool = False,
    pmid_anchor: str | None = None,
) -> dict[str, Any]:
    """v2.2 P1-#10 helper — call this from any Wave-3 Monte Carlo / model
    fit site that uses a literature-anchored parameter. Returns a record
    suitable for inclusion in ``analysis_runs[i].calibration[]``.

    Provenance is one of: paper_derived / informed_estimate / literature_default.
    """
    provenance = classify_calibration_provenance(
        extracted_quote=extracted_quote,
        was_from_full_text=was_from_full_text,
        used_default=used_default,
    )
    return {
        "parameter_name": parameter_name,
        "value": value,
        "parameter_calibration": provenance.value,
        "extracted_quote": extracted_quote,
        "pmid_anchor": pmid_anchor,
    }


# Type alias — Wave 3 accepts either compute runner. They share the
# ``run_notebook(notebook_path=, workdir=, timeout_s=)`` interface returning
# a ``BixbenchRunResult``. v1.5 added ``NativeAnalysisRunner`` to remove the
# Docker dependency on the critical path (docs/ANTI_PATTERNS_v1.4.md AP-1).
ComputeRunner = BixbenchRunner | NativeAnalysisRunner


class Wave3Runner:
    """End-to-end Wave 3 data-evidence driver.

    v1.5: ``bixbench`` param widened to accept ``NativeAnalysisRunner`` as
    well. The field is still named ``self.bixbench`` for back-compat with
    existing tests + downstream code; the runtime check goes by interface
    (``run_notebook``) not by class.
    """

    def __init__(
        self,
        *,
        out_dir: Path,
        aviv: LLMBackedExpert,
        bixbench: ComputeRunner,
        tyler: LLMBackedExpert | None = None,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.aviv = aviv
        self.tyler = tyler
        self.bixbench: ComputeRunner = bixbench
        # v1.5.2: optional plain-language progress reporter — drives the
        # "[3/5 查数据 / Cross-checking]" stage. None = no-op for back-compat.
        self.reporter = reporter

    async def run(
        self,
        patient_text: str,
        patient_context: dict[str, Any],
        wave2_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = f"wave3_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        run_dir = self.out_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        prov = ProvenanceJournal(run_dir / "provenance.jsonl")

        hypotheses = wave2_outputs.get("hypotheses", [])
        top_k_ids = [hid for hid, _ in wave2_outputs.get("top_k", [])][:3]

        # v1.5.2: stage-3 start (lay label "查数据 / Cross-checking").
        # Internal Wave 3 has three sub-stages (dataset / analysis /
        # validation) but the user sees one "查数据" stage with heartbeats.
        if self.reporter is not None:
            self.reporter.start_stage(
                3,
                action_zh=(
                    "在公开数据库 (TCGA / cBioPortal 这种)里对照您的肿瘤特征"
                ),
            )

        # Stage 1 — dataset_acquisition (Aviv)
        ds_context = {
            **patient_context,
            "profile_json": json.dumps(patient_context, ensure_ascii=False),
            "ngs_report": patient_context.get("ngs_report", ""),
            "wave2_hypotheses": json.dumps(hypotheses, ensure_ascii=False),
        }
        datasets_out = await self.aviv.execute(
            task_package="dataset_acquisition",
            plan={"task_packages": ["dataset_acquisition"]},
            context=ds_context,
        )
        prov.append(
            {
                "stage": "dataset_acquisition",
                "hash": hash_claim({"out": datasets_out}),
            }
        )
        if self.reporter is not None:
            n_top = len(top_k_ids)
            self.reporter.heartbeat(
                3,
                f"匹配的公开数据集找到了, 准备拿您的前 {n_top} 个方案逐个去对照",
                force=True,
            )

        # Stage 2 — bioinformatics_data_analysis (Aviv) — one plan per top-hyp
        analysis_runs: list[dict[str, Any]] = []
        for hid in top_k_ids:
            hyp = next((h for h in hypotheses if h.get("id") == hid), None)
            if hyp is None:
                continue
            ba_context = {
                **patient_context,
                "profile_json": json.dumps(patient_context, ensure_ascii=False),
                "datasets_json": json.dumps(datasets_out, ensure_ascii=False),
                "hypothesis_text": hyp.get("text", ""),
            }
            plan_out = await self.aviv.execute(
                task_package="bioinformatics_data_analysis",
                plan={"task_packages": ["bioinformatics_data_analysis"]},
                context=ba_context,
            )
            # bixbench dry-run (live only if OPL_BIXBENCH_LIVE=1)
            nb_path = run_dir / f"{hid}_analysis.ipynb"
            nb_path.write_text("{}", encoding="utf-8")
            bix_result = self.bixbench.run_notebook(
                notebook_path=nb_path, workdir=run_dir, timeout_s=600
            )
            analysis_runs.append(
                {
                    "hyp_id": hid,
                    "analysis_plan": plan_out,
                    "bixbench_result": bix_result.to_dict(),
                }
            )
            prov.append(
                {
                    "stage": "bioinformatics_data_analysis",
                    "hyp_id": hid,
                    "bix_mode": bix_result.mode,
                }
            )
            # Heartbeat per analyzed top-K hypothesis (only fires if
            # ≥ heartbeat_interval since the last emit — protects
            # against spammy chat in fast batches).
            if self.reporter is not None:
                self.reporter.heartbeat(
                    3,
                    f"第 {len(analysis_runs)} / {len(top_k_ids)} 个方案的数据对照已完成",
                )

        # Stage 3 — hypothesis_validation (Tyler if present, else Aviv)
        validator = self.tyler if self.tyler is not None else self.aviv
        validations: list[dict[str, Any]] = []
        for run in analysis_runs:
            hid = run["hyp_id"]
            hyp = next((h for h in hypotheses if h.get("id") == hid), None)
            if hyp is None:
                continue
            hv_context = {
                **patient_context,
                "profile_json": json.dumps(patient_context, ensure_ascii=False),
                "hypothesis_json": json.dumps(hyp, ensure_ascii=False),
                "wave3_evidence": json.dumps(run, ensure_ascii=False),
            }
            verdict = await validator.execute(
                task_package="hypothesis_validation",
                plan={"task_packages": ["hypothesis_validation"]},
                context=hv_context,
            )
            validations.append({"hyp_id": hid, "validator": validator.profile.name, "verdict": verdict})
            prov.append(
                {
                    "stage": "hypothesis_validation",
                    "hyp_id": hid,
                    "validator": validator.profile.name,
                }
            )

        payload: dict[str, Any] = {
            "run_id": run_id,
            "patient_text": patient_text,
            "datasets": datasets_out,
            "analysis_runs": analysis_runs,
            "validations": validations,
        }
        out_path = run_dir / "wave3_data_evidence.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # v2.5.1 B3 — same fakery_sniffer + reviewer pairing discipline as
        # wave1_runner. Wave 3 hosts Aviv as the primary expert; reviewer
        # pairing routes to (bert | maya) per the existing expert pairing
        # matrix in orchestrator.reviewer_hook.
        post_write_safety_check(out_path, run_root=run_dir)
        from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing
        run_reviewer_pairing(
            report_path=out_path,
            primary_expert="aviv",
            primary_model="claude-opus-4-7",
        )
        # v1.5.2: stage-3 end. Surface a lay summary; next stage is "审核".
        if self.reporter is not None:
            n_validated = len(validations)
            self.reporter.end_stage(
                3,
                summary_zh=(
                    f"{n_validated} 个方案都用公开数据库对照过了, 部分结论有了新的支撑"
                ),
                next_stage_preview_zh=(
                    "审核 — 我们的内部审查员会一条一条核对证据强不强"
                ),
            )
        return payload
