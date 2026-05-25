"""G7: Imperative-detector — block command-form leakage. Spec §7 G7 / C1.

Scans claim text fields for imperative patterns ("you should / must / 应该 /
必须 / 立即 / 建议立即") and FAILs (block=True) unless the surrounding sentence
ALSO carries a PMID / NCT / source URL token AND a risk-caveat keyword
("may", "risk", "side effect", "可能", "副作用", "风险").

Runs over a recursive walk of all string fields in the claim dict — catches
nested fields like ``symptom_plan[].intervention``.

P1-6 — strict_imperative_isolation
----------------------------------
The default same-sentence rule has a known LLM-learnable bypass: a single
sentence stuffing imperative + bare PMID + risk keyword passes even though
the structure ("You must take drug X PMID:12345 — risk of bleeding.") is
exactly the spoof shape clinical reviewers worry about. Setting
``strict_imperative_isolation=True`` additionally requires that within the
sentence containing the imperative, **the imperative clause itself must not
contain a bare (non-parenthesised) PMID/NCT/URL token** — evidence must
either live in a separate clause (split on commas, semicolons, em-dashes,
parens) or be parenthesised as is conventional in clinical citations.

Default stays ``False`` for backwards compatibility; v1.6 will flip it on.
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# Patterns chosen for high precision + low false-positive on clinical text.
_EN_IMPERATIVE = re.compile(
    r"\b(you\s+(should|must)|must\s+(give|start|apply|take|stop)|"
    r"start\s+(immediately|now)\b)",
    re.IGNORECASE,
)
_ZH_IMPERATIVE = re.compile(r"(应该|必须|建议立即|立即停用|立即开始)")

_EVIDENCE_TOKEN = re.compile(
    r"(PMID[:\s]?\d+|NCT\d{8}|https?://[^\s,]+)", re.IGNORECASE
)
_RISK_KEYWORD = re.compile(
    r"\b(may|risk|side\s+effect|adverse|caution|warning)\b|(可能|副作用|风险|不良反应)",
    re.IGNORECASE,
)

# Sentence splitter — keeps period/question/exclamation/中文句号问号叹号.
_SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+|\n+")

# Clause splitter used in strict mode: commas, semicolons, em-dashes, parens.
# Note: colon is intentionally excluded because it splits "PMID:12345" mid-token.
_CLAUSE_SPLIT = re.compile(r"[,;()\[\]]|—|--|\s-\s")

# Citation-form evidence: parenthesised/bracketed PMID/NCT/URL.
_CITED_EVIDENCE = re.compile(
    r"[\(\[][^()\[\]]*?(PMID[:\s]?\d+|NCT\d{8}|https?://[^\s,)]+)[^()\[\]]*?[\)\]]",
    re.IGNORECASE,
)


def _walk_strings(node: Any) -> list[str]:
    """Recursively collect all string values in a claim dict."""
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            out.extend(_walk_strings(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_walk_strings(v))
    return out


class G7ImperativeDetectorGate(Gate):
    name = "G7_imperative_detector"
    description = (
        "Block command-form (imperative) recommendations unless sentence "
        "carries PMID/NCT/URL evidence + risk caveat."
    )
    failure_mode_code = "C1"

    def __init__(self, *, strict_imperative_isolation: bool = False) -> None:
        """Construct G7 gate.

        Args:
            strict_imperative_isolation: when True, additionally require that
                the imperative clause itself does NOT carry a bare (non-parenthesised)
                PMID/NCT/URL. Evidence must live in a separate clause or be
                citation-formatted. Closes the single-sentence bypass.
        """
        self.strict_imperative_isolation = strict_imperative_isolation

    def check(self, claim: dict[str, Any]) -> GateResult:
        strings = _walk_strings(claim)
        offenders: list[str] = []
        for blob in strings:
            for sent in _SENT_SPLIT.split(blob):
                sent_stripped = sent.strip()
                if not sent_stripped:
                    continue
                if not (
                    _EN_IMPERATIVE.search(sent_stripped)
                    or _ZH_IMPERATIVE.search(sent_stripped)
                ):
                    continue
                has_evidence = bool(_EVIDENCE_TOKEN.search(sent_stripped))
                has_risk = bool(_RISK_KEYWORD.search(sent_stripped))
                if not (has_evidence and has_risk):
                    offenders.append(sent_stripped[:200])
                    continue
                if self.strict_imperative_isolation and self._has_bare_evidence_in_imperative_clause(
                    sent_stripped
                ):
                    offenders.append(sent_stripped[:200])
        if offenders:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"imperative phrasing without PMID+risk caveat in "
                    f"{len(offenders)} sentence(s)"
                ),
                evidence={"offending_sentences": offenders},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message="no imperative-without-evidence detected",
        )

    def _has_bare_evidence_in_imperative_clause(self, sentence: str) -> bool:
        """Strict mode: find the clause containing the imperative; check it
        carries a bare (non-parenthesised) PMID/NCT/URL token. If yes, this is
        the single-sentence spoof pattern — FAIL.
        """
        for clause in _CLAUSE_SPLIT.split(sentence):
            clause_stripped = clause.strip()
            if not clause_stripped:
                continue
            if not (
                _EN_IMPERATIVE.search(clause_stripped)
                or _ZH_IMPERATIVE.search(clause_stripped)
            ):
                continue
            bare_evidence = _EVIDENCE_TOKEN.search(clause_stripped)
            if not bare_evidence:
                continue
            # The token is in the imperative clause. Is it citation-formatted?
            cited = _CITED_EVIDENCE.search(sentence)
            if cited and cited.group(1) == bare_evidence.group(0):
                # Same token appears parenthesised elsewhere; treat as cited.
                continue
            # Bare PMID/NCT/URL inside an imperative clause = the spoof shape.
            return True
        return False
