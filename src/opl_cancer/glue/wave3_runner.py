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
memory:feedback_no_offline_only — no silent network fallback; integrators raise.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.compute.runner import BixbenchRunner
from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal


class Wave3Runner:
    """End-to-end Wave 3 data-evidence driver."""

    def __init__(
        self,
        *,
        out_dir: Path,
        aviv: LLMBackedExpert,
        bixbench: BixbenchRunner,
        tyler: LLMBackedExpert | None = None,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.aviv = aviv
        self.tyler = tyler
        self.bixbench = bixbench

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
        (run_dir / "wave3_data_evidence.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload
