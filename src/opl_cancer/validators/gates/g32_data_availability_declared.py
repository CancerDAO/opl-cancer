"""G32: data_availability_declared — Wave 6 manuscript invariant.

Spec §5.3 (ADR-0023). The bundle's ``reproducibility.md`` MUST list every
data source the manuscript references along with an explicit access tier:

* ``public`` — open data (TCGA open tier, ClinicalTrials.gov, PubMed,
  OpenTargets, etc.)
* ``DUA`` — Data Use Agreement required (TCGA controlled access, CPTAC
  restricted, dbGaP)
* ``patient-private`` — the individual patient's records.

Any line that says "patient" / "EHR" / "private records" without a tier
label OR that uses a tier value outside the allow-list fails the gate.

Caller passes:
* ``reproducibility_path`` — direct path, OR
* ``bundle_root`` — directory containing ``reproducibility.md``, OR
* ``reproducibility_text`` — raw markdown string.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


ALLOWED_TIERS = {"public", "dua", "patient-private"}

# Section heading detection — we require a "## Data sources" / "## Data
# availability" section in reproducibility.md.
_DATA_SECTION_RE = re.compile(
    r"^#{1,4}\s*(?:data\s+(?:sources|availability)|sources?|data)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Each data source MUST appear as a markdown list item ending with a
# `tier: <value>` annotation. Example acceptable lines:
#   - TCGA-LUAD RNA-seq, tier: public
#   - 007-zhiqiang EHR records, tier: patient-private
#   - cBioPortal MSK Lung 2023 cohort (tier: public)
_LINE_TIER_RE = re.compile(
    r"tier\s*[:=]\s*[\"']?(public|dua|patient[-_ ]?private)[\"']?",
    re.IGNORECASE,
)
_LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+")

# Hints that a line mentions a data source even if untagged.
_PATIENT_HINTS_RE = re.compile(
    r"\b(patient|EHR|electronic\s+health|private\s+record|N=1|n[\s-]of[\s-]1)\b",
    re.IGNORECASE,
)


def _resolve_text(claim: dict[str, Any]) -> tuple[str, str]:
    if (path_str := claim.get("reproducibility_path")):
        p = Path(path_str)
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    if (text := claim.get("reproducibility_text")):
        return str(text), "inline"
    if (root := claim.get("bundle_root")):
        p = Path(root) / "reproducibility.md"
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    return "", "no_field"


class G32DataAvailabilityDeclaredGate(Gate):
    name = "G32_data_availability_declared"
    description = (
        "reproducibility.md must list every data source with an explicit "
        "access tier (public | DUA | patient-private). Patient-private "
        "sources must be labeled."
    )
    failure_mode_code = "F-WAVE6-DATA-AVAILABILITY"

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
                message=f"G32 SKIP — non-wave6 stage {stage!r}",
            )

        text, source = _resolve_text(claim)
        if not text:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G32 FAIL — reproducibility.md missing or empty "
                    f"(source={source})."
                ),
                evidence={"source": source},
            )

        section_hit = bool(_DATA_SECTION_RE.search(text))
        if not section_hit:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G32 FAIL — reproducibility.md has no '## Data sources' / "
                    "'## Data availability' section. Add one and tier-label "
                    "every data source."
                ),
                evidence={"source": source},
            )

        # Walk list items inside / after the data section.
        in_data_section = False
        tiered = 0
        untagged_lines: list[tuple[int, str]] = []
        unknown_tier_lines: list[tuple[int, str, str]] = []
        for i, line in enumerate(text.splitlines(), start=1):
            if _DATA_SECTION_RE.match(line):
                in_data_section = True
                continue
            # Leaving the section when we hit another heading.
            if in_data_section and re.match(r"^#{1,4}\s+", line):
                in_data_section = False
                continue
            if not in_data_section:
                continue
            if not _LIST_ITEM_RE.match(line):
                continue
            m = _LINE_TIER_RE.search(line)
            if not m:
                # Check if the line mentions a data source at all
                if _PATIENT_HINTS_RE.search(line):
                    untagged_lines.append((i, line.strip()[:140]))
                continue
            tier_raw = m.group(1).lower().replace("_", "-").replace(" ", "-")
            if tier_raw not in ALLOWED_TIERS:
                unknown_tier_lines.append((i, tier_raw, line.strip()[:140]))
                continue
            tiered += 1

        if untagged_lines:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G32 FAIL — {len(untagged_lines)} data-source line(s) "
                    "mention patient / EHR but lack `tier: ...` annotation. "
                    "Patient-private sources MUST be labeled."
                ),
                evidence={
                    "source": source,
                    "untagged": [
                        {"line": ln, "text": t} for ln, t in untagged_lines[:10]
                    ],
                    "remediation": "append_tier_patient-private",
                },
            )

        if unknown_tier_lines:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G32 FAIL — {len(unknown_tier_lines)} data-source line(s) "
                    "use unknown tier value(s). Allowed: public, DUA, patient-private."
                ),
                evidence={
                    "source": source,
                    "unknown": [
                        {"line": ln, "tier": t, "text": txt}
                        for ln, t, txt in unknown_tier_lines[:10]
                    ],
                },
            )

        if tiered == 0:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G32 FAIL — data section is empty (no tier-tagged list items)."
                ),
                evidence={"source": source},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"G32 OK — {tiered} data source(s) tier-labeled.",
            evidence={"source": source, "tiered_count": tiered},
        )
