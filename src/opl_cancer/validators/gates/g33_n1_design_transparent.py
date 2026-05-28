"""G33: n1_design_transparent — Wave 6 manuscript invariant.

Spec §5.3 (ADR-0023). The manuscript's methods section MUST explicitly
declare a single-subject (N=1) design. Any use of "cohort" / "population"
language WITHOUT an N=1 caveat is flagged as a generalization risk.

Caller passes EITHER:
* ``manuscript_methods_path`` — path to `manuscript_methods.md` or the
  rendered methods section, OR
* ``manuscript_methods_text`` — raw text, OR
* ``bundle_root`` — directory; gate first looks for
  ``manuscript_methods.md`` and, if absent, scans ``manuscript.md`` for
  the methods section.

Failure mode F-WAVE6-N1-GENERALIZATION: shipping an N=1 case as if it
were a cohort study — the most common reviewer red-flag for case reports.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# Acceptable N=1 declaration phrases. We're permissive on phrasing.
_N1_DECL_RE = re.compile(
    r"\b(?:single[-\s]subject|single[-\s]patient|n\s*=\s*1|n[-\s]of[-\s]1|"
    r"individual\s+patient|case\s+report)\b",
    re.IGNORECASE,
)

# Generalization language that needs an N=1 caveat nearby. We treat these
# as "red-flag" tokens; they're allowed only if the same sentence (or the
# immediately preceding sentence) also contains the N=1 caveat.
_RISKY_RE = re.compile(
    r"\b(cohort|population|patient\s+population|general\s+population|"
    r"all\s+patients|n\s*=\s*\d{2,}|prospective\s+study|retrospective\s+study)\b",
    re.IGNORECASE,
)

# Caveat tokens that legitimize cohort/population mentions.
_CAVEAT_RE = re.compile(
    r"\b(?:single[-\s]subject|n\s*=\s*1|n[-\s]of[-\s]1|"
    r"applied\s+to\s+this\s+individual|projected\s+to\s+this\s+(?:patient|subject)|"
    r"in\s+contrast\s+to|unlike\s+cohort|for\s+reference|background)\b",
    re.IGNORECASE,
)

_METHODS_HEADING_RE = re.compile(
    r"^#{1,4}\s*(?:methods|materials\s+and\s+methods|design)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _resolve_methods_text(claim: dict[str, Any]) -> tuple[str, str]:
    if (p := claim.get("manuscript_methods_path")):
        path = Path(p)
        if path.is_file():
            return path.read_text(encoding="utf-8"), str(path)
        return "", f"missing:{path}"
    if (t := claim.get("manuscript_methods_text")):
        return str(t), "inline"
    if (root := claim.get("bundle_root")):
        # First try a standalone methods file.
        ms = Path(root) / "manuscript_methods.md"
        if ms.is_file():
            return ms.read_text(encoding="utf-8"), str(ms)
        manuscript = Path(root) / "manuscript.md"
        if manuscript.is_file():
            full = manuscript.read_text(encoding="utf-8")
            return _extract_methods_section(full), str(manuscript)
    return "", "no_field"


def _extract_methods_section(full: str) -> str:
    """Return text from '## Methods' to the next heading at same or higher level."""
    lines = full.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _METHODS_HEADING_RE.match(line):
            start = i
            break
    if start is None:
        return ""
    # Find next heading at same/higher level.
    start_hashes = len(lines[start]) - len(lines[start].lstrip("#"))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        m = re.match(r"^(#{1,4})\s+", line)
        if m and len(m.group(1)) <= start_hashes:
            end = j
            break
    return "\n".join(lines[start:end])


def _split_sentences(text: str) -> list[str]:
    """Crude sentence splitter (period / question / exclaim).
    Good enough for the mechanical scan."""
    # Strip code fences first.
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?。！？])\s+", cleaned)
        if s.strip()
    ]


class G33N1DesignTransparentGate(Gate):
    name = "G33_n1_design_transparent"
    description = (
        "manuscript_methods.md (or methods section in manuscript.md) MUST "
        "contain explicit 'single-subject (N=1) design' language. Any "
        "cohort/population language without an N=1 caveat is flagged."
    )
    failure_mode_code = "F-WAVE6-N1-GENERALIZATION"

    def check(self, claim: dict[str, Any]) -> GateResult:
        stage = (claim.get("run_stage") or claim.get("wave") or "").lower()
        if stage and not (
            "wave6" in stage
            or stage in {"manuscript", "n1a_bundle", "delivery"}
            or stage == "6"
        ):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"G33 SKIP — non-wave6 stage {stage!r}",
            )

        text, source = _resolve_methods_text(claim)
        if not text:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G33 FAIL — methods text missing or empty (source={source})."
                ),
                evidence={"source": source},
            )

        # Step 1: must contain an explicit N=1 declaration.
        if not _N1_DECL_RE.search(text):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G33 FAIL — methods text lacks explicit N=1 / single-subject "
                    "declaration. Add a sentence like 'This is a single-subject "
                    "(N=1) report.'"
                ),
                evidence={
                    "source": source,
                    "remediation": "add_explicit_n1_declaration",
                },
            )

        # Step 2: flag risky cohort/population language without caveat.
        sentences = _split_sentences(text)
        flagged: list[tuple[int, str]] = []
        for idx, s in enumerate(sentences):
            if _RISKY_RE.search(s):
                # Caveat MUST be in the same sentence. A general N=1
                # declaration in an earlier sentence does not legitimize a
                # later unhedged cohort claim — the reader can lose the
                # framing across paragraphs.
                if _CAVEAT_RE.search(s):
                    continue
                flagged.append((idx, s[:160]))

        if flagged:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G33 FAIL — {len(flagged)} sentence(s) use cohort/population "
                    "language without an N=1 caveat. Either rephrase or add a "
                    "caveat token (e.g. 'for reference', 'in contrast to')."
                ),
                evidence={
                    "source": source,
                    "flagged": [
                        {"sentence_index": i, "text": t} for i, t in flagged[:10]
                    ],
                    "remediation": "rephrase_or_add_caveat",
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message="G33 OK — explicit N=1 design declared; no unhedged cohort language.",
            evidence={"source": source},
        )
