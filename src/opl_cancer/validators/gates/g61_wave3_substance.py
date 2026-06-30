"""G61: wave3_substance_executed — Wave-3 quantitative evidence must be COMPUTED.

Failure mode (substance gap, first-principles audit 2026-06-30): the Wave-3
compute runners (`NativeAnalysisRunner` / `BixbenchRunner`) default to dry-run
unless ``OPL_NATIVE_LIVE=1`` / ``OPL_BIXBENCH_LIVE=1`` is set. A dry-run still
writes non-empty metadata into ``wave3_data_evidence.json`` (analysis plans,
notebook stubs), so the existing hollow-run detector — which checks *emptiness*
— passes. The result: a patient brief can present quantitative predictions
(pooled HR/OR, 95% CI, Cox/KM survival) that were NEVER actually computed,
dressed as measured evidence. G25 only catches claims explicitly LABELLED
``[SKIPPED]`` / ``deferred=true``; it cannot see a dry-run masquerading as a
real result.

G61 closes that hole deterministically (no LLM, no network): if a run
materialised Wave-3 analysis runs but EVERY one executed in a dry-run mode,
delivery BLOCKS. The brief must not claim measured numbers the engine never
produced. To run for real: set ``OPL_NATIVE_LIVE=1`` (jupyter) or
``OPL_BIXBENCH_LIVE=1`` (docker), or run on a machine where the chosen runtime
is available (preflight already refuses to start a patient run without one).

This mirrors SKILL.md principle #7 ("Real prediction, not just labelling —
Wave 3 outputs are quantitative") and the no-silent-skip doctrine
(docs/ANTI_PATTERNS_v1.4.md AP-1).

Input (claim dict): ``run_dir`` — the run directory holding
``wave3_data_evidence.json``. Sync, no network.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import json

from ..mechanical_gates import Gate, GateResult, GateStatus

# A mode string counts as "executed for real" when it ends with "live"
# (``live`` / ``native-live``). Anything containing "dry-run" is un-computed.
_DRY = "dry-run"


def _is_live_mode(mode: str) -> bool:
    m = (mode or "").strip().lower()
    return m.endswith("live") and _DRY not in m


class G61Wave3SubstanceGate(Gate):
    """Wave-3 analysis must be actually computed, not dry-run metadata."""

    name = "G61_wave3_substance_executed"
    description = (
        "If a run materialised Wave-3 analysis runs, at least one must have "
        "executed in a live mode. A brief built on dry-run-only Wave-3 evidence "
        "presents un-computed numbers as measured — BLOCK."
    )
    failure_mode_code = "F-SUBSTANCE-W3"

    def _evidence_path(self, claim: dict[str, Any]) -> Path | None:
        rd = claim.get("run_dir")
        if rd:
            p = Path(rd) / "wave3_data_evidence.json"
            return p if p.exists() else None
        # allow a direct path override
        ep = claim.get("wave3_evidence_path")
        if ep and Path(ep).exists():
            return Path(ep)
        return None

    def check(self, claim: dict[str, Any]) -> GateResult:
        path = self._evidence_path(claim)
        if path is None:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G61 SKIP — no wave3_data_evidence.json to inspect "
                        "(absent-evidence case is owned by G25 / delivery_runner).",
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=f"G61 FAIL — wave3_data_evidence.json unreadable: {e}",
            )
        if not isinstance(payload, dict):
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G61 FAIL — wave3_data_evidence.json is not an object.",
            )

        runs = payload.get("analysis_runs") or []
        if not isinstance(runs, list) or not runs:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G61 SKIP — no Wave-3 analysis runs materialised; nothing "
                        "quantitative to verify here.",
            )

        # A top-level analysis_mode summary, if the runner wrote one, is the
        # authoritative signal (e.g. native path executed live while bix was
        # skipped) and overrides the per-run scan.
        top_mode = str(payload.get("analysis_mode") or "").strip().lower()
        if top_mode:
            if _is_live_mode(top_mode):
                return GateResult(
                    gate=self.name, status=GateStatus.PASS,
                    message=f"G61 OK — Wave-3 analysis_mode={top_mode} (executed).",
                )
            if _DRY in top_mode:
                return self._block(runs, "analysis_mode=" + top_mode)

        modes: list[str] = []
        for r in runs:
            br = (r or {}).get("bixbench_result") or {}
            modes.append(str(br.get("mode") or ""))
        if any(_is_live_mode(m) for m in modes):
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message=f"G61 OK — {sum(_is_live_mode(m) for m in modes)}/{len(modes)} "
                        "Wave-3 analysis run(s) executed live.",
            )
        return self._block(runs, "all runs: " + ", ".join(m or "?" for m in modes))

    def _block(self, runs: list[Any], detail: str) -> GateResult:
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                "G61 FAIL — Wave-3 analysis executed in dry-run mode ONLY "
                f"({detail}). The brief would present un-computed quantitative "
                "predictions (HR/CI/Cox/KM) as measured evidence. Set "
                "OPL_NATIVE_LIVE=1 (jupyter) or OPL_BIXBENCH_LIVE=1 (docker), or "
                "run where the chosen runtime is available — do not ship "
                "un-computed numbers."
            ),
            evidence={"n_runs": len(runs), "detail": detail},
        )
