"""G10: guideline citations must declare version + date. Spec §7 G10 / §6.5 D2.

Failure mode D2 — stale guideline ("NCCN says…" without version).
Rules:
  * Any evidence record with `source` in {NCCN, CSCO, ESMO, ASCO, AHA} OR
    `type == "guideline"` MUST carry both a `version` AND a `date` field.
  * If date > 12 months old → reviewer flag (WARN, block=False) — does NOT
    block, but surfaces "guideline may be stale" to Reviewer.

Date parsing accepts ISO YYYY-MM-DD, YYYY/MM, or YYYY.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_GUIDELINE_SOURCES = {"NCCN", "CSCO", "ESMO", "ASCO", "AHA", "ASH", "EAU", "EHA"}
_DATE_PATTERNS = (
    re.compile(r"^(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"^(\d{4})/(\d{2})$"),
    re.compile(r"^(\d{4})\.(\d{2})$"),
    re.compile(r"^(\d{4})$"),
)


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for pat in _DATE_PATTERNS:
        m = pat.match(s)
        if not m:
            continue
        groups = m.groups()
        try:
            if len(groups) == 3:
                return date(int(groups[0]), int(groups[1]), int(groups[2]))
            if len(groups) == 2:
                return date(int(groups[0]), int(groups[1]), 1)
            return date(int(groups[0]), 1, 1)
        except ValueError:
            return None
    return None


def _is_guideline(e: dict[str, Any]) -> bool:
    if e.get("type") == "guideline":
        return True
    src = (e.get("source") or e.get("publisher") or "").upper()
    return any(g in src for g in _GUIDELINE_SOURCES)


class G10GuidelineVersionGate(Gate):
    name = "G10_guideline_version"
    description = "Guideline citations must declare version + date; >12 mo → reviewer flag."
    failure_mode_code = "D2"

    def __init__(self, today: date | None = None, stale_months: int = 12) -> None:
        self.today = today or datetime.now(timezone.utc).date()
        self.stale_months = stale_months

    def check(self, claim: dict[str, Any]) -> GateResult:
        guidelines = [e for e in claim.get("evidence", []) if _is_guideline(e)]
        if not guidelines:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no guideline citations"
            )
        missing: list[dict[str, Any]] = []
        stale: list[dict[str, Any]] = []
        for e in guidelines:
            version = e.get("version")
            date_str = e.get("date") or e.get("year")
            if not version or not date_str:
                missing.append(
                    {"id": e.get("id"), "source": e.get("source"), "version": version,
                     "date": date_str}
                )
                continue
            parsed = _parse_date(str(date_str))
            if parsed is None:
                missing.append(
                    {"id": e.get("id"), "reason": f"date not parseable: {date_str!r}"}
                )
                continue
            age_days = (self.today - parsed).days
            if age_days > self.stale_months * 30:
                stale.append(
                    {"id": e.get("id"), "source": e.get("source"), "version": version,
                     "date": str(parsed), "age_days": age_days}
                )
        if missing:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"{len(missing)} guideline citation(s) missing version or date",
                evidence={"missing": missing, "stale": stale},
            )
        if stale:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,
                message=f"{len(stale)} guideline citation(s) >{self.stale_months} mo old",
                evidence={"stale": stale, "reviewer_flag": True},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"all {len(guidelines)} guideline(s) versioned + fresh",
        )
