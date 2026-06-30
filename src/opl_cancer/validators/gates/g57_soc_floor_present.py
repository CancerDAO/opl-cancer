"""G57: soc_floor_present — the delivered brief must anchor the standard-of-care FLOOR.

Closes the second hole the jessie run-opl-20260629 review found: the run leapt to
a 'transcendence' frontier (ATR / TROP2 / trials) but SKIPPED the stage-appropriate
standard of care — for a locoregional (N3) recurrence treated with definitive RT,
the global floor is PACIFIC-style consolidation immunotherapy, and the brief never
asked 'why not durvalumab consolidation?'. A research brief that climbs above the
guideline without first naming the floor is not safe: the patient can't tell a
beyond-SoC bet from the SoC they should already be on.

G57 enforces that the delivery carries an explicit standard-of-care floor anchor.
Mechanically (deterministic, no LLM): at least one delivered brief must contain the
``[SOC-FLOOR]`` marker AND a stage statement. The marker forces the author to write
the floor section (stage → stage-appropriate standard) rather than only the
frontier. Cheap to satisfy honestly, impossible to satisfy by skipping the floor.

Sync, no network. Caller passes ``out_dir`` (delivery dir) or ``brief_path``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_FLOOR_MARKER = re.compile(r"\[SOC-?FLOOR\]", re.I)
_STAGE = re.compile(r"\b(?:stage|分期|IV|III|II|N[0-3]|M[01]|局部区域|locoregional|metastatic|转移)\b", re.I)
_BRIEF_GLOBS = ("*brief.md", "*brief.html", "patient_brief.html")


class G57SoCFloorPresentGate(Gate):
    """A delivered brief must anchor the stage-appropriate standard-of-care floor."""

    name = "G57_soc_floor_present"
    description = (
        "At least one delivered brief must carry an explicit [SOC-FLOOR] anchor + a "
        "stage statement — the stage-appropriate standard of care named BEFORE any "
        "beyond-guideline frontier. A frontier-only brief that skips the floor "
        "(e.g. omits PACIFIC consolidation for post-RT locoregional disease) BLOCKS."
    )
    failure_mode_code = "AP-FLOOR-SKIPPED"
    family_id = "completeness"

    def _briefs(self, claim: dict[str, Any]) -> list[Path]:
        out = claim.get("out_dir")
        bp = claim.get("brief_path")
        files: list[Path] = []
        if bp and Path(bp).is_file():
            files.append(Path(bp))
        if out:
            d = Path(out)
            for g in _BRIEF_GLOBS:
                files.extend(d.glob(g))
        # de-dup
        seen: set[str] = set()
        uniq: list[Path] = []
        for f in files:
            if str(f) not in seen:
                seen.add(str(f))
                uniq.append(f)
        return uniq

    def check(self, claim: dict[str, Any]) -> GateResult:
        briefs = self._briefs(claim)
        if not briefs:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G57 SKIP — no delivered brief to check.")
        marker_ok = False
        stage_ok = False
        for bp in briefs:
            try:
                text = bp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _FLOOR_MARKER.search(text):
                marker_ok = True
            if _STAGE.search(text):
                stage_ok = True
        if marker_ok and stage_ok:
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message="G57 OK — brief anchors the standard-of-care floor ([SOC-FLOOR] + stage).",
            )
        missing = []
        if not marker_ok:
            missing.append("[SOC-FLOOR] anchor (name the stage-appropriate standard before the frontier)")
        if not stage_ok:
            missing.append("a stage statement")
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                "G57 FAIL — delivered brief does not anchor the SoC floor: missing "
                + " and ".join(missing) + ". OPL must name the stage-appropriate "
                "standard of care (e.g. PACIFIC consolidation for post-definitive-RT "
                "locoregional disease) BEFORE any beyond-guideline option."
            ),
            evidence={"briefs": [b.name for b in briefs], "marker_ok": marker_ok, "stage_ok": stage_ok},
        )
