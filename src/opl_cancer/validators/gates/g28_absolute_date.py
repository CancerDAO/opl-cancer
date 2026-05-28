"""G28: absolute_date — close the v2.1 LLM "5 weeks → 5 months" failure mode.

Spec §4.3 P1-#15.

A claim that uses relative date language (`X mo/week/day ago`, `约 N 月前`,
`approximately three months back`, etc.) MUST also carry an explicit
`from_date` + `to_date` pair on the claim object. Otherwise FAIL + block.

`[BACKGROUND]`-tagged sentences are exempt (informational prose, not a
clinical claim). This is the same exemption convention G30 (manuscript
claim PMID anchor, v2.3) will reuse.

The gate is intentionally regex-driven (no LLM in the loop) — the v2.1
postmortem confirmed that the failure mode is the LLM mis-counting time,
so a mechanical anchor is the right cut.
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# English relative-date phrases. We require a leading numeric (digit or
# small English count word) immediately followed by a unit word.
_NUMERIC_WORDS = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|a|an|several|few|couple|approximately|about|around|roughly)"
_UNIT_WORDS = r"(?:mo|month|months|wk|week|weeks|day|days|yr|year|years|hr|hour|hours)"

_RELATIVE_EN_RE = re.compile(
    rf"\b(?:\d+|{_NUMERIC_WORDS})\s+{_UNIT_WORDS}\s+(?:ago|back|prior|earlier|later)\b",
    re.IGNORECASE,
)

# Approximate + unit phrasing (no "ago" required, still ambiguous).
_RELATIVE_EN_APPROX_RE = re.compile(
    rf"\b(?:approximately|about|around|roughly|~)\s+\d+\s+{_UNIT_WORDS}\b",
    re.IGNORECASE,
)

# Chinese relative-date phrases. Pattern: 数字 + 周/月/年/天 + 前/以前/之前.
# Also covers 几 / 数 prefix.
_RELATIVE_ZH_RE = re.compile(
    r"(?:\d+|[一二三四五六七八九十几数])\s*(?:周|个?月|年|天|小时)\s*(?:前|以前|之前)"
)

# `[BACKGROUND]` tag exemption — anywhere in the claim text bypasses G28.
_BACKGROUND_RE = re.compile(r"\[BACKGROUND\]", re.IGNORECASE)


def _claim_text(claim: dict[str, Any]) -> str:
    """Join all human-prose fields of a claim into one string for scanning."""
    parts = [
        claim.get("claim", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("rationale", ""),
    ]
    return "\n".join(str(p) for p in parts if p)


def _has_relative_date(text: str) -> tuple[bool, str]:
    """Return (matched, first_match_text)."""
    for rx in (_RELATIVE_EN_RE, _RELATIVE_EN_APPROX_RE, _RELATIVE_ZH_RE):
        m = rx.search(text)
        if m:
            return True, m.group(0)
    return False, ""


def _has_date_anchor(claim: dict[str, Any]) -> bool:
    return bool(claim.get("from_date")) and bool(claim.get("to_date"))


class G28AbsoluteDateGate(Gate):
    name = "G28_absolute_date"
    description = (
        "Relative date language (`X mo/week/day ago`, `~N months`, 中文「N 月前」) "
        "MUST carry an explicit from_date + to_date pair, or be tagged "
        "[BACKGROUND]. Closes the v2.1 LLM-confused-weeks-for-months failure mode."
    )
    failure_mode_code = "F_REL_DATE"

    def check(self, claim: dict[str, Any]) -> GateResult:
        text = _claim_text(claim)
        if not text.strip():
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="G28 OK — empty claim text",
            )

        if _BACKGROUND_RE.search(text):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G28 SKIP — [BACKGROUND] tag exempts informational prose",
            )

        matched, match_text = _has_relative_date(text)
        if not matched:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="G28 OK — no relative date language detected",
            )

        if _has_date_anchor(claim):
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    f"G28 OK — relative phrase {match_text!r} present but "
                    "claim carries from_date+to_date anchor"
                ),
                evidence={
                    "relative_phrase": match_text,
                    "from_date": claim.get("from_date"),
                    "to_date": claim.get("to_date"),
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=True,
            message=(
                f"G28 FAIL — claim contains relative date {match_text!r} "
                "but no `from_date`+`to_date` anchor. Either add an absolute "
                "date pair or tag the sentence [BACKGROUND]. This closes the "
                "v2.1 LLM-confused-weeks-for-months failure mode."
            ),
            evidence={
                "relative_phrase": match_text,
                "remediation": "add_from_date_and_to_date_or_tag_background",
            },
        )
