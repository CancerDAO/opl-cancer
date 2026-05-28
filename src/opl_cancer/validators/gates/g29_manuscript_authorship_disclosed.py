"""G29: manuscript_authorship_disclosed — Wave 6 manuscript invariant.

Spec §5.3 (ADR-0023). When OPL emits a Wave 6 manuscript, the bundle
MUST contain `ai_authorship_disclosure.md` and that file MUST:

1. List EACH contributing expert (CRediT-style contribution table).
2. State explicitly that "no human author beyond patient & supervising
   clinician" — the founder-mode philosophy applied to publication.

Failure mode F-WAVE6-AUTHORSHIP: shipping a manuscript whose AI co-authorship
is hidden or partial. The N1Arxiv submission contract (v2.4) also enforces
this gate on the CI side, but G29 catches it pre-bundle.

The gate is path-driven: it accepts a claim dict with either:

* ``ai_authorship_disclosure_path`` — Path to the file, OR
* ``ai_authorship_disclosure`` — the raw text, OR
* ``bundle_root`` — directory containing ``ai_authorship_disclosure.md``

If none is present, the gate FAILs (block=True) because absence of
disclosure IS the failure mode this gate guards against.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# Phrases that satisfy the "no human author beyond patient & clinician"
# attestation. We're permissive on phrasing — any of these patterns counts.
_NO_HUMAN_AUTHOR_RE = re.compile(
    r"(no\s+human\s+(?:co-?)?author(?:s)?\s+(?:beyond|other than|except)\s+"
    r"(?:the\s+)?patient\s+(?:and|&)\s+(?:supervising\s+)?clinician|"
    r"only\s+(?:the\s+)?patient\s+(?:and|&)\s+(?:supervising\s+)?clinician)",
    re.IGNORECASE,
)

# A "contribution table" or CRediT-style listing. We accept either a markdown
# table header containing "Expert" or a heading like "## Contributions".
_CONTRIB_TABLE_RE = re.compile(
    r"\|\s*(?:expert|contributor|author)\s*\|",
    re.IGNORECASE,
)
_CONTRIB_HEADING_RE = re.compile(
    r"^#{1,4}\s*(?:contribut|credit|author)",
    re.IGNORECASE | re.MULTILINE,
)


def _resolve_disclosure_text(claim: dict[str, Any]) -> tuple[str, str]:
    """Return (text, source_label). Empty text → missing disclosure."""
    if (path_str := claim.get("ai_authorship_disclosure_path")):
        p = Path(path_str)
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    if (text := claim.get("ai_authorship_disclosure")):
        return str(text), "inline"
    if (root := claim.get("bundle_root")):
        p = Path(root) / "ai_authorship_disclosure.md"
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    return "", "no_disclosure_field"


class G29ManuscriptAuthorshipDisclosedGate(Gate):
    name = "G29_manuscript_authorship_disclosed"
    description = (
        "Wave 6 manuscript MUST ship ai_authorship_disclosure.md containing "
        "(a) per-expert CRediT-style contribution table AND (b) explicit "
        "attestation: no human author beyond patient & supervising clinician."
    )
    failure_mode_code = "F-WAVE6-AUTHORSHIP"

    # Minimum number of named experts required in the disclosure table.
    # OPL ships 20 experts + Henry; even a partial run should name ≥ 1.
    MIN_EXPERTS_LISTED = 1

    def check(self, claim: dict[str, Any]) -> GateResult:
        # Only enforce at Wave 6 / delivery stage. Other waves SKIP.
        stage = (claim.get("run_stage") or claim.get("wave") or "").lower()
        if stage and not (
            "wave6" in stage
            or stage in {"manuscript", "n1a_bundle", "delivery"}
            or stage == "6"
        ):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"G29 SKIP — non-wave6 stage {stage!r}",
            )

        text, source = _resolve_disclosure_text(claim)
        if not text:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G29 FAIL — ai_authorship_disclosure.md missing or empty "
                    f"(source={source}). Wave 6 manuscript may not ship "
                    "without explicit AI authorship disclosure."
                ),
                evidence={"source": source},
            )

        # Check the attestation phrase.
        attestation_hit = bool(_NO_HUMAN_AUTHOR_RE.search(text))
        if not attestation_hit:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G29 FAIL — disclosure lacks the required attestation: "
                    "'no human author beyond patient & supervising clinician' "
                    "(or equivalent phrasing). This is the founder-mode "
                    "honesty invariant for Wave 6."
                ),
                evidence={
                    "source": source,
                    "remediation": "add_no_human_author_attestation_sentence",
                },
            )

        # Check at least one contribution-table header is present.
        contrib_hit = bool(
            _CONTRIB_TABLE_RE.search(text) or _CONTRIB_HEADING_RE.search(text)
        )
        if not contrib_hit:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "G29 FAIL — disclosure has no CRediT-style contribution "
                    "table (markdown table with 'Expert' / 'Contributor' "
                    "header) and no '## Contributions' / '## Authorship' "
                    "section. Each contributing expert must be named."
                ),
                evidence={
                    "source": source,
                    "remediation": "add_credit_contribution_table",
                },
            )

        # Bonus: extract named experts from the text. We look for the canonical
        # 20-expert roster + Henry. Lower-bound check on count.
        roster = {
            "rosa", "bert", "vince", "rick", "heddy", "mary", "aviv", "tyler",
            "iain", "ted", "riad", "jen", "kieren", "mark", "hong", "frances",
            "dennis", "steve", "maya", "julius", "henry",
        }
        text_lower = text.lower()
        named = sorted({e for e in roster if re.search(rf"\b{e}\b", text_lower)})
        if len(named) < self.MIN_EXPERTS_LISTED:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G29 FAIL — disclosure names {len(named)} expert(s); "
                    f"minimum required is {self.MIN_EXPERTS_LISTED}. Wave 6 "
                    "manuscript invariant: every contributing expert listed."
                ),
                evidence={"source": source, "experts_found": named},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G29 OK — disclosure attests no-human-author and lists "
                f"{len(named)} expert(s)."
            ),
            evidence={"source": source, "experts_found": named},
        )
