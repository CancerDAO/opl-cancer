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
# Honest escape: the brief may declare that no STANDARD OF CARE remains for this
# patient (a genuine late-line reality) instead of fabricating a floor. Tightened
# to require "standard of care" / 标准治疗 specifically — "no standard chemotherapy"
# is NOT a no-SoC declaration (adversarial review 2026-06-30).
_NO_SOC = re.compile(
    r"no\s+(?:remaining\s+)?standard\s+of\s+care(?:\s+remains?)?"
    r"|standard\s+of\s+care\s+(?:is\s+)?exhausted"
    r"|no\s+remaining\s+(?:standard\s+)?(?:treatment|therapy|guideline\s+option)"
    r"|标准治疗(?:已)?(?:用尽|耗尽|无)|无(?:可用)?标准治疗|无标准(?:治疗)?方案",
    re.I,
)
# Unfinished-scaffold markers that must not count as a real floor. Note: HTML tags
# are stripped BEFORE this runs (so <p>/<h2> don't read as placeholders); the
# only angle-bracket token we treat as a placeholder is an explicit <insert ...>.
_PLACEHOLDER = re.compile(
    r"\bTBD\b|\bTODO\b|\bTK\b|\bPENDING\b|coming\s+soon|fill\s*[- ]?in|to\s+be\s+"
    r"(?:filled|completed|determined|added)|待填充|待补|待定|占位|<\s*insert|XXX+|\.\.\.\s*$",
    re.I,
)
# A real floor NAMES a standard of care — it must carry at least one treatment /
# guideline content signal, not just 25 chars of filler (adversarial review:
# "aaaa bbbb ... Stage IV" passed a length-only check).
_SOC_CONTENT = re.compile(
    r"standard\s+of\s+care|consolidation|maintenance|chemo(?:therapy)?|regimen|"
    r"immunotherapy|radiation|radiotherapy|surgery|targeted|guideline|nccn|csco|"
    r"esmo|first[- ]line|second[- ]line|\bSoC\b|[a-z]{4,}(?:mab|nib|tinib|platin|"
    r"rubicin|lizumab)\b|化疗|放疗|靶向|免疫|手术|标准方案|标准治疗|指南|巩固|维持|一线|二线|三线",
    re.I,
)
_HTML_TAG = re.compile(r"<[^>]+>")
# Minimum real (whitespace-normalised) characters of floor content after the
# marker for the section to count as substantive (not a bare heading).
_MIN_FLOOR_CHARS = 25


def _floor_window(text: str, marker_start: int) -> str:
    """Text from a [SOC-FLOOR] marker to the next markdown heading (or 800 chars)."""
    rest = text[marker_start:]
    nl = rest.find("\n")
    after = rest[nl + 1:] if nl != -1 else ""
    nxt = re.search(r"\n#{1,6}\s", after)
    end = nxt.start() if nxt else min(len(after), 800)
    return rest[: (nl + 1 if nl != -1 else 0)] + after[:end]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


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
        # Tightened (adversarial review 2026-06-30): marker + stage + substance
        # must be CO-LOCATED in the marker's own section, not OR-ed across the
        # whole brief — else a hollow "## [SOC-FLOOR] TBD" heading plus the word
        # "metastatic" in a trial title elsewhere would pass. We scan the window
        # from each [SOC-FLOOR] marker to the next markdown heading (or 800 chars)
        # and require, within it: a stage token AND either a substantive named
        # standard OR an explicit honest "no standard remains" declaration.
        best: dict[str, Any] | None = None
        for bp in briefs:
            try:
                text = bp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in _FLOOR_MARKER.finditer(text):
                window = _floor_window(text, m.start())
                # strip HTML tags first so an HTML brief's <p>/<h2> neither read
                # as placeholders nor pad the substance length.
                window = _HTML_TAG.sub(" ", window)
                stage_ok = bool(_STAGE.search(window))
                honest_none = bool(_NO_SOC.search(window))
                # substance = real, NAMED standard-of-care content beyond the
                # marker — not a placeholder and not 25 chars of filler. Requires
                # an actual treatment/guideline signal (_SOC_CONTENT).
                body = _FLOOR_MARKER.sub(" ", window)
                placeholder = bool(_PLACEHOLDER.search(body))
                substance_ok = (
                    len(_norm(body)) >= _MIN_FLOOR_CHARS
                    and not placeholder
                    and bool(_SOC_CONTENT.search(body))
                )
                cand = {"brief": bp.name, "stage_ok": stage_ok,
                        "honest_none": honest_none, "substance_ok": substance_ok,
                        "placeholder": placeholder}
                if honest_none and not placeholder:
                    return GateResult(
                        gate=self.name, status=GateStatus.PASS,
                        message="G57 OK — brief honestly declares no remaining "
                                "standard of care ([SOC-FLOOR] + explicit none).",
                        evidence=cand,
                    )
                if stage_ok and substance_ok:
                    return GateResult(
                        gate=self.name, status=GateStatus.PASS,
                        message="G57 OK — brief anchors the standard-of-care floor "
                                "([SOC-FLOOR] + stage + named standard).",
                        evidence=cand,
                    )
                # keep the most-complete failing window for the message
                score = stage_ok + substance_ok + honest_none
                if best is None or score > best.get("_score", -1):
                    best = {**cand, "_score": score}

        if best is None:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G57 FAIL — no [SOC-FLOOR] anchor in any delivered brief. "
                        "OPL must name the stage-appropriate standard of care (e.g. "
                        "PACIFIC consolidation for post-definitive-RT locoregional "
                        "disease) BEFORE any beyond-guideline option — or honestly "
                        "declare no standard remains.",
                evidence={"briefs": [b.name for b in briefs]},
            )
        missing = []
        if not best["stage_ok"]:
            missing.append("a stage statement in the [SOC-FLOOR] section")
        if not best["substance_ok"]:
            missing.append(
                "a substantive named standard (the section is empty/placeholder)"
                if best["placeholder"] or not best["stage_ok"]
                else "a substantive named standard of care"
            )
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                "G57 FAIL — the [SOC-FLOOR] section is present but hollow: missing "
                + " and ".join(missing) + ". Name the stage-appropriate standard of "
                "care BEFORE any beyond-guideline option, or honestly declare that no "
                "standard remains."
            ),
            evidence={k: v for k, v in best.items() if k != "_score"},
        )
