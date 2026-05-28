"""G30: claim_pmid_anchored — Wave 6 manuscript invariant.

Spec §5.3 (ADR-0023). Every claim sentence in `manuscript.md` MUST end
with one of:

* ``[PMID:XXXXXXX]`` — anchored to a PubMed ID, OR
* ``[integrator:NAME run_id:HASH]`` — anchored to a deterministic
  integrator run (cBioPortal cohort, COSMIC signature, Monte Carlo, …)

Sentences leading with ``[BACKGROUND]`` are exempt (informational prose,
not a clinical claim — same convention as G28).

The gate operates on the manuscript text. Caller may pass:

* ``manuscript_path`` — path to manuscript.md, OR
* ``manuscript_text`` — raw markdown string, OR
* ``bundle_root`` — directory containing ``manuscript.md``.

Sentences inside fenced code blocks, markdown tables, headings, and
empty lines are NOT treated as claim sentences (they don't make claims).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# Patterns the closing anchor of every claim sentence may match.
_PMID_ANCHOR_RE = re.compile(
    r"\[PMID\s*:\s*\d{4,9}\](?:\s*[.;:,?!\)\]])*\s*$",
    re.IGNORECASE,
)
# run_id is hex SHA-256 in production but allow any alphanumeric token
# so test fixtures + reference-case bundles can use human-readable IDs.
_INTEGRATOR_ANCHOR_RE = re.compile(
    r"\[integrator\s*:\s*[A-Za-z0-9_.\-]+\s+run_id\s*:\s*[A-Za-z0-9_\-]+\](?:\s*[.;:,?!\)\]])*\s*$",
    re.IGNORECASE,
)
# `[BACKGROUND]` tag exempts a claim sentence from PMID anchoring. To be
# robust against markdown bold/italic prefixes (e.g. "**Background.**
# [BACKGROUND] ..."), we allow the tag anywhere in the sentence — same
# convention as G28.
_BACKGROUND_TAG_RE = re.compile(r"\[BACKGROUND\]", re.IGNORECASE)
_HEADING_RE = re.compile(r"^\s{0,3}#")
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_FENCE_RE = re.compile(r"^\s*```")
_BLOCKQUOTE_RE = re.compile(r"^\s*>")


def _resolve_manuscript_text(claim: dict[str, Any]) -> tuple[str, str]:
    if (path_str := claim.get("manuscript_path")):
        p = Path(path_str)
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    if (text := claim.get("manuscript_text")):
        return str(text), "inline"
    if (root := claim.get("bundle_root")):
        p = Path(root) / "manuscript.md"
        if p.is_file():
            return p.read_text(encoding="utf-8"), str(p)
        return "", f"missing:{p}"
    return "", "no_manuscript_field"


def _iter_claim_sentences(text: str) -> list[tuple[int, str]]:
    """Yield (line_number, sentence_text) of lines that are claim-bearing
    prose. Skips code fences, headings, tables, blockquotes, blanks.

    We treat each non-empty prose line as one "sentence" for the purpose
    of anchor enforcement. This is intentionally aggressive — Wave 6 task
    packages are required to emit one-sentence-per-line claim paragraphs
    so the mechanical scan stays simple.
    """
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, raw in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        if _HEADING_RE.match(raw):
            continue
        if _TABLE_ROW_RE.match(raw):
            continue
        if _BLOCKQUOTE_RE.match(raw):
            continue
        # Strip leading list markers but keep the sentence content.
        m = re.match(r"^(\s*[-*+]\s+|\s*\d+\.\s+)", raw)
        sentence = raw[m.end():].strip() if m else stripped
        if not sentence:
            continue
        out.append((i, sentence))
    return out


def _has_anchor(sentence: str) -> bool:
    return bool(_PMID_ANCHOR_RE.search(sentence) or _INTEGRATOR_ANCHOR_RE.search(sentence))


class G30ClaimPMIDAnchoredGate(Gate):
    name = "G30_claim_pmid_anchored"
    description = (
        "Every claim sentence in manuscript.md must end with [PMID:XXXXX] "
        "or [integrator:NAME run_id:HASH]. [BACKGROUND]-tagged sentences "
        "are exempt (same convention as G28)."
    )
    failure_mode_code = "F-WAVE6-CLAIM-UNANCHORED"
    # v2.5 RFC 0001 §2.5 — provenance gate family migration.
    family_id = "provenance"

    # If a manuscript has 0 claim sentences (e.g. abstract-only stub) we
    # SKIP rather than PASS, so callers can detect "no claims to anchor".
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
                message=f"G30 SKIP — non-wave6 stage {stage!r}",
            )

        text, source = _resolve_manuscript_text(claim)
        if not text:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G30 FAIL — manuscript.md missing or empty (source={source})."
                ),
                evidence={"source": source},
            )

        sentences = _iter_claim_sentences(text)
        if not sentences:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G30 SKIP — no claim-bearing sentences detected.",
                evidence={"source": source},
            )

        unanchored: list[tuple[int, str]] = []
        for ln, sentence in sentences:
            if _BACKGROUND_TAG_RE.search(sentence):
                continue
            if _has_anchor(sentence):
                continue
            unanchored.append((ln, sentence[:140]))

        if unanchored:
            sample = "; ".join(
                f"L{ln}: {s!r}" for ln, s in unanchored[:5]
            )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G30 FAIL — {len(unanchored)} claim sentence(s) lack "
                    "[PMID:...] or [integrator:NAME run_id:HASH] anchor. "
                    f"First failures: {sample}. Tag with [BACKGROUND] if "
                    "not a clinical claim."
                ),
                evidence={
                    "source": source,
                    "unanchored_count": len(unanchored),
                    "first_failures": [
                        {"line": ln, "sentence": s} for ln, s in unanchored[:10]
                    ],
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G30 OK — all {len(sentences)} claim sentence(s) PMID/integrator-anchored."
            ),
            evidence={
                "source": source,
                "sentence_count": len(sentences),
            },
        )
