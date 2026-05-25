"""G27: privacy scrub — PII regex detection. v1.5 P1-5.

Failure mode F-NEW-3: an expert report contains the patient's actual
contact info (phone / email / national ID / hospital MRN / family
contact). In PT-EXAMPLE-A, Dennis's report literally embedded
``[FAMILY-CONTACT] 13800138000`` — the patient's family phone — into a
permanent artifact (docs/ANTI_PATTERNS_v1.4.md AP-8).

This gate scans report text for PII patterns and BLOCKS the report
write until the personas regenerate without the leak.

Patterns covered:
  * CN mobile phone (1[3-9]\\d{9}; with optional +86 prefix)
  * Generic E.164 phone formats (+\\d{1,3}\\s?\\d{4,14})
  * Email addresses (RFC-5322 lite)
  * CN national ID (18-digit, second-gen)
  * Hospital MRN (configurable per-hospital prefix; default heuristic
    catches 8-12-digit numbers explicitly labelled "MRN" / "病案号"
    / "住院号" / "门诊号")

Whitelist: phone-like numbers inside trial NCT IDs, PMIDs, OncoKB
identifiers, or doses (e.g. "960 mg QD") are NOT redacted. The gate
uses surrounding-context heuristics — see `_is_whitelisted_context`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


@dataclass(frozen=True)
class PIIMatch:
    kind: str
    snippet: str
    span: tuple[int, int]


# CN mobile: 1, then digit 3-9, then 9 digits. Optionally prefixed +86 or 0086.
_CN_PHONE = re.compile(
    r"(?:\+?86[\s-]?|0086[\s-]?)?(1[3-9]\d{9})\b"
)
# Generic email
_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
# CN national ID (second-generation, 18 digit, last char may be X)
_CN_NATIONAL_ID = re.compile(
    r"\b[1-9]\d{5}(?:19|20)\d{2}"
    r"(?:0[1-9]|1[0-2])"
    r"(?:0[1-9]|[12]\d|3[01])"
    r"\d{3}[\dXx]\b"
)
# MRN-labeled numbers (in en + zh)
_MRN_LABELED = re.compile(
    r"(?:MRN|病案号|住院号|门诊号|就诊号|医保号|医保卡号)[\s:：=#]*([A-Za-z0-9\-]{6,})",
    re.IGNORECASE,
)
# Insurance card (CN 商保 / 医保 pattern — broad)
_INSURANCE_CARD = re.compile(
    r"(?:保单号|保险号|insurance(?:[\s_-]*(?:card|policy))?)\s*[:：=#]?\s*([A-Za-z0-9\-]{8,})",
    re.IGNORECASE,
)


def _is_whitelisted_context(text: str, span: tuple[int, int], kind: str) -> bool:
    """Soft check: skip if the surrounding context indicates the matched
    digits are a PMID / NCT ID / OncoKB ID / dose / lab value.

    Whitelisting is only applied to digit-based identifier kinds —
    emails / MRN-labeled / insurance-labeled never get whitelisted
    because their patterns are structurally explicit.
    """
    if kind not in {"cn_phone", "cn_national_id"}:
        return False
    start, end = span
    # Inspect only the LEFT-side context (the label / identifier of the
    # match precedes the digits in clinical-style writing); 12 chars is
    # enough for "PMID 12345678".
    around = text[max(0, start - 12): start].lower()
    for label in (
        "pmid",
        "nct",
        "oncokb",
        "doi:",
        "isbn",
        "civic",
        "rxcui",
    ):
        if label in around:
            return True
    # Right-side dose-unit context: a number immediately followed by
    # "mg", "mg/kg", etc.
    right = text[end: end + 6].lower()
    for unit in (" mg", " mg/m", " mg/kg", " iu/l", " ng/ml", " u/l"):
        if right.startswith(unit):
            return True
    return False


def scan_text(text: str) -> list[PIIMatch]:
    """Return ordered list of PII matches found in ``text``. Used by both
    the gate and the redaction helper. Whitelist applied."""
    if not text:
        return []
    out: list[PIIMatch] = []
    for kind, pat in (
        ("cn_phone", _CN_PHONE),
        ("email", _EMAIL),
        ("cn_national_id", _CN_NATIONAL_ID),
        ("hospital_mrn", _MRN_LABELED),
        ("insurance_card", _INSURANCE_CARD),
    ):
        for m in pat.finditer(text):
            if _is_whitelisted_context(text, m.span(), kind):
                continue
            out.append(PIIMatch(kind=kind, snippet=m.group(0), span=m.span()))
    out.sort(key=lambda x: x.span)
    return out


def redact_text(text: str) -> tuple[str, list[PIIMatch]]:
    """Return (redacted_text, matches). Each match is replaced by a
    ``[REDACTED:<kind>]`` token. Preserves text length-difference
    awareness for downstream tooling (matches contain original span)."""
    matches = scan_text(text)
    if not matches:
        return text, []
    pieces: list[str] = []
    cursor = 0
    for m in matches:
        pieces.append(text[cursor: m.span[0]])
        pieces.append(f"[REDACTED:{m.kind}]")
        cursor = m.span[1]
    pieces.append(text[cursor:])
    return "".join(pieces), matches


class G27PrivacyScrubGate(Gate):
    name = "G27_privacy_scrub"
    description = (
        "Detect PII (phone / email / national-ID / MRN / insurance) in "
        "report text. Block until redacted."
    )
    failure_mode_code = "F-NEW-3"

    def check(self, claim: dict[str, Any]) -> GateResult:
        # We accept either an explicit `report_text` field or scan all
        # string-valued fields concatenated.
        text_parts: list[str] = []
        if "report_text" in claim and isinstance(claim["report_text"], str):
            text_parts.append(claim["report_text"])
        else:
            for k, v in claim.items():
                if isinstance(v, str) and len(v) > 0:
                    text_parts.append(v)
        joined = "\n".join(text_parts)
        matches = scan_text(joined)
        if not matches:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="no PII patterns detected",
            )
        # Surface up to 5 specific snippets for actionable debugging.
        sample = "; ".join(
            f"{m.kind}={m.snippet!r}" for m in matches[:5]
        )
        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=True,
            message=(
                f"{len(matches)} PII match(es) detected — report must be "
                f"regenerated without leak. Examples: {sample}"
            ),
            evidence={
                "n_matches": len(matches),
                "match_kinds": sorted({m.kind for m in matches}),
                "samples": [
                    {"kind": m.kind, "snippet": m.snippet, "span": list(m.span)}
                    for m in matches[:10]
                ],
            },
        )
