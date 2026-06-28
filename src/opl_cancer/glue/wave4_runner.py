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
no-silent-fallback policy — no silent network fallback; integrators raise.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.glue._post_write import post_write_safety_check
from opl_cancer.glue.surprise_replan import spawn_surprise_replan
# NOTE (harness-split): orchestrator.* is the self-improvement engine being
# extracted to a standalone repo. Imported lazily (in-function) so this runner
# stays importable when orchestrator/ is absent. ``run_reviewer_pairing`` stays
# exposed as a module attribute via PEP 562 ``__getattr__`` for the B3 wiring
# contract (test_sniffer_halt_wave4).
from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal


def __getattr__(name: str):  # PEP 562 — lazy orchestrator re-export
    if name == "run_reviewer_pairing":
        from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing
        return run_reviewer_pairing
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _read_surprise_signal(
    hyp: dict[str, Any], aviv_verdict: dict[str, Any]
) -> tuple[bool, bool, str | None]:
    """D3/ADR-0036 — read Aviv's LLM surprise judgment (no Python keyword judgment).

    A forecast can only be *contradicted* if the hypothesis carried a locked
    forecast (prior_expectation). Aviv signals it directly (``contradicts_forecast``)
    or via ``updated_belief.surprise == 'strong'``; a strange-tail anomaly is its
    own flag. The testability_path (how to chase it) is Aviv's too.
    """
    ub = aviv_verdict.get("updated_belief")
    ub = ub if isinstance(ub, dict) else {}
    has_forecast = bool(isinstance(hyp.get("prior_expectation"), dict) and hyp.get("prior_expectation"))
    contradicted = has_forecast and (
        bool(aviv_verdict.get("contradicts_forecast"))
        or str(ub.get("surprise", "")).lower() == "strong"
    )
    anomaly = bool(aviv_verdict.get("strange_tail_anomaly"))
    tp = aviv_verdict.get("surprise_testability_path") or ub.get("testability_path")
    return contradicted, anomaly, (str(tp) if tp else None)


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
        replans: list[dict[str, Any]] = []
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

            # D3/ADR-0036 — follow the surprise: a Wave-3 result that contradicts
            # the locked forecast (or is a strange-tail anomaly) becomes a promoted
            # replan task, not just a failure-ledger line. Detection is Aviv's LLM
            # judgment; spawn_surprise_replan enforces the testability_path guard.
            contradicted, anomaly, tp = _read_surprise_signal(hyp, aviv_verdict)
            if contradicted or anomaly:
                replans.append(spawn_surprise_replan(
                    self.out_dir,
                    hypothesis_id=hid,
                    contradicted=contradicted,
                    anomaly=anomaly,
                    testability_path=tp,
                    trigger_detail=str(
                        (aviv_verdict.get("updated_belief") or {}).get("what_changed", "")
                    ),
                ))

        payload: dict[str, Any] = {
            "run_id": run_id,
            "patient_text": patient_text,
            "validations": results,
            "n_validated": sum(1 for r in results if r["survival_status"] == "validated"),
            "n_falsified": sum(1 for r in results if r["survival_status"] == "falsified"),
            "n_inconclusive": sum(
                1 for r in results if r["survival_status"] == "inconclusive"
            ),
            # D3/ADR-0036 — replan tasks spawned for chased surprises (empty when none).
            "replans": replans,
        }
        out_path = run_dir / "wave4_validation.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # v2.5.1 B3 — same fakery_sniffer + reviewer pairing discipline as
        # wave1_runner. Wave 4 has Aviv as primary validator and Iain as
        # the meta-validator; we pair against Aviv to keep distinct-expert
        # constraint satisfied (Iain → aviv pairing exists in the matrix).
        post_write_safety_check(out_path, run_root=run_dir)
        from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing
        run_reviewer_pairing(
            report_path=out_path,
            primary_expert="aviv",
            primary_model="claude-opus-4-7",
        )
        return payload
