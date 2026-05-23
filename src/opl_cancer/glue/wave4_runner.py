"""Wave 4 hypothesis-validation orchestrator. P4.5-T4.

Drives Aviv (leads) + Iain (meta-validator) through:
    1. For each Wave-2 top hypothesis with Wave-3 data evidence — Aviv issues
       a domain validation verdict (data-anchored).
    2. Iain meta-validates Aviv's verdict via Cochrane-lens audit (risk-of-bias,
       quality-of-evidence, contradiction with prior literature).
    3. Each hypothesis is classified into survival_status:
         - ``validated`` — both Aviv pass + Iain pass
         - ``falsified`` — Aviv fail (data contradicts)
         - ``inconclusive`` — Aviv pass but Iain flags issues OR insufficient data

Writes ``triggers/<run_id>/wave4_validation.json`` + provenance.jsonl.
Per ADR-2026-04-22 main-thread sequential awaits.
memory:feedback_no_offline_only — no silent network fallback; integrators raise.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal


def _classify(aviv_verdict: dict[str, Any], iain_verdict: dict[str, Any]) -> str:
    # Aviv hypothesis_validation returns ``verdict`` (supported / weakened /
    # falsified / inconclusive). We also accept ``validation_status`` for
    # forward compatibility with Wave4-specific verdicts.
    a_status = str(
        aviv_verdict.get("verdict", aviv_verdict.get("validation_status", ""))
    ).lower()
    i_status = str(
        iain_verdict.get("meta_verdict", iain_verdict.get("verdict", ""))
    ).lower()
    if a_status in {"falsified", "fail", "contradicted"}:
        return "falsified"
    if a_status in {"validated", "pass", "supported"} and i_status in {
        "pass",
        "validated",
        "ok",
        "supported",
    }:
        return "validated"
    return "inconclusive"


class Wave4Runner:
    """End-to-end Wave 4 hypothesis-validation driver."""

    def __init__(
        self,
        *,
        out_dir: Path,
        aviv: LLMBackedExpert,
        iain: LLMBackedExpert,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.aviv = aviv
        self.iain = iain

    async def run(
        self,
        patient_text: str,
        patient_context: dict[str, Any],
        wave2_outputs: dict[str, Any],
        wave3_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = f"wave4_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        run_dir = self.out_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        prov = ProvenanceJournal(run_dir / "provenance.jsonl")

        hypotheses = wave2_outputs.get("hypotheses", [])
        top_k_ids = [hid for hid, _ in wave2_outputs.get("top_k", [])][:3]
        wave3_validations = {
            v["hyp_id"]: v for v in wave3_outputs.get("validations", [])
        }
        wave3_analysis = {
            a["hyp_id"]: a for a in wave3_outputs.get("analysis_runs", [])
        }

        results: list[dict[str, Any]] = []
        for hid in top_k_ids:
            hyp = next((h for h in hypotheses if h.get("id") == hid), None)
            if hyp is None:
                continue

            # Stage 1 — Aviv issues data-anchored validation verdict
            aviv_ctx = {
                **patient_context,
                "profile_json": json.dumps(patient_context, ensure_ascii=False),
                "hypothesis_json": json.dumps(hyp, ensure_ascii=False),
                "wave3_evidence": json.dumps(
                    {
                        "wave3_validation": wave3_validations.get(hid, {}),
                        "wave3_analysis": wave3_analysis.get(hid, {}),
                    },
                    ensure_ascii=False,
                ),
            }
            aviv_verdict = await self.aviv.execute(
                task_package="hypothesis_validation",
                plan={"task_packages": ["hypothesis_validation"]},
                context=aviv_ctx,
            )
            prov.append(
                {
                    "stage": "wave4_aviv_validate",
                    "hyp_id": hid,
                    "hash": hash_claim({"out": aviv_verdict}),
                }
            )

            # Stage 2 — Iain meta-validates (Cochrane lens) over hypothesis
            # + aviv's data verdict. meta_analysis template needs
            # cancer_type_stage + sub_goal + pubmed_results placeholders.
            iain_ctx = {
                **patient_context,
                "profile_json": json.dumps(patient_context, ensure_ascii=False),
                "hypothesis_json": json.dumps(hyp, ensure_ascii=False),
                "aviv_verdict_json": json.dumps(aviv_verdict, ensure_ascii=False),
                "wave3_evidence": aviv_ctx["wave3_evidence"],
                "cancer_type_stage": patient_context.get("cancer_type_stage", "unspecified"),
                "sub_goal": f"meta-validate hypothesis {hid}",
                "pubmed_results": json.dumps(
                    patient_context.get("pubmed_results", []), ensure_ascii=False
                ),
            }
            iain_verdict = await self.iain.execute(
                task_package="meta_analysis",
                plan={"task_packages": ["meta_analysis"]},
                context=iain_ctx,
            )
            prov.append(
                {
                    "stage": "wave4_iain_meta",
                    "hyp_id": hid,
                    "hash": hash_claim({"out": iain_verdict}),
                }
            )

            survival_status = _classify(aviv_verdict, iain_verdict)
            results.append(
                {
                    "hyp_id": hid,
                    "hypothesis_text": hyp.get("text", ""),
                    "aviv_verdict": aviv_verdict,
                    "iain_meta_verdict": iain_verdict,
                    "survival_status": survival_status,
                    "evidence_layer": aviv_verdict.get(
                        "claim_layer_summary", "exploratory"
                    ),
                }
            )

        payload: dict[str, Any] = {
            "run_id": run_id,
            "patient_text": patient_text,
            "validations": results,
            "n_validated": sum(1 for r in results if r["survival_status"] == "validated"),
            "n_falsified": sum(1 for r in results if r["survival_status"] == "falsified"),
            "n_inconclusive": sum(
                1 for r in results if r["survival_status"] == "inconclusive"
            ),
        }
        (run_dir / "wave4_validation.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload
