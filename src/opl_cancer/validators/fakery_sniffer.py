"""v2.1 P1-#9: fakery sniffer.

Scans artifacts (md / text content extracted from json) for placeholder
language that indicates the LLM fabricated rather than retrieved. Flagged
claims freeze downstream waves and auto-trigger
``patient_pushback_handling``.

Exemptions:

* Lines starting with ``[BACKGROUND]`` are exempt — the SKILL uses this
  marker for epidemiology / introduction snippets where order-of-magnitude
  language is appropriate.

ADR-0021 invariant: every artifact persisted by a wave runner passes
through ``scan_artifact``; a non-empty list means a wave-halt + a
SNIFFER_HALT.md emit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Patterns operate per line. Anchored with word boundaries so we don't
# over-fire on legitimate prose ("estimated" inside "underestimated").
_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\[(speculative|projected|structural template|placeholder)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(estimated|approximately|on the order of|likely between)\s+\d",
        re.IGNORECASE,
    ),
    re.compile(r"<insert (PMID|citation|value)>", re.IGNORECASE),
    # ── v2.6.0: CJK (Chinese-primary) placeholder language ──
    # OPL is Chinese-primary; the English-only set above was blind to the
    # delivery scaffold's zh placeholders ("这一节由 SKILL 主线程的 LLM 填充").
    # Patterns are scoped to placeholder *contexts* so they don't over-fire on
    # legitimate clinical prose (e.g. 假体填充 / 主治医生 must NOT match).
    re.compile(r"占位符?"),  # 占位 / 占位符 (placeholder)
    re.compile(r"待(补充|填写|填|确定|完善|定|续写|生成)"),  # 待填写 / 待补充 …
    re.compile(r"(填充|填写|插入|补全|生成)(本节|本段|此处|这一节|这里|本题|此题)"),
    re.compile(
        r"(主线程|SKILL\s*主线程|main[\s-]?thread)[^\n]{0,16}(填充|填写|生成|补全|fill)",
        re.IGNORECASE,
    ),
    re.compile(r"由\s*(SKILL|主线程|LLM)[^\n]{0,16}填充", re.IGNORECASE),
    re.compile(r"\b(TODO|TBD|FIXME|XXX)\b", re.IGNORECASE),
    re.compile(r"待办(事项)?[:：]"),
]


@dataclass(frozen=True)
class FakeryFinding:
    excerpt: str
    pattern: str
    line_number: int


def scan_text(text: str) -> Iterator[FakeryFinding]:
    """Yield findings line-by-line, skipping [BACKGROUND]-tagged lines."""
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("[BACKGROUND]"):
            continue
        for pat in _PATTERNS:
            if pat.search(line):
                yield FakeryFinding(
                    excerpt=stripped,
                    pattern=pat.pattern,
                    line_number=i,
                )


def scan_artifact(path: Path) -> list[FakeryFinding]:
    """Scan a file by path; returns list of findings (empty if clean)."""
    text = Path(path).read_text(encoding="utf-8")
    return list(scan_text(text))


# ── v2.10 P0.3d: confident-but-unanchored fabrication signals in a brief ─────
# The placeholder set above catches a brief that *admits* it is unfinished
# (TODO / 待填充 / <insert PMID>). It is blind to the more dangerous case the
# red-team reproduced: a brief that states a confident efficacy number or a
# specific drug+dose with NO backing gated claim — i.e. a fabricated fact that
# reads as finished, authoritative prose.
#
# These signals are graded SOFT (flag-for-review) by default — we are
# deliberately conservative to avoid false positives on legitimate, properly
# gated clinical prose. The caller (delivery_gate_runner) decides whether an
# unanchored signal escalates to a hard block based on whether the brief has a
# gated-claims record at all.

# Efficacy / response / survival numbers. ORR / DCR / PFS / OS / median /
# response rate / 缓解率 / 客观缓解率 / 中位 with an attached percentage or
# month/year figure. We require the metric token AND a number to fire.
_EFFICACY_RE = re.compile(
    r"(?:"
    r"ORR|DCR|PFS|OS|CR|PR|HR(?:\s*[=:])|"
    r"objective\s+response|response\s+rate|disease\s+control|"
    r"overall\s+survival|progression[\s-]?free\s+survival|median(?:\s+(?:OS|PFS|survival))?|"
    r"客观缓解率?|缓解率|疾病控制率?|无进展生存(?:期|时间)?|总生存(?:期|时间)?|中位(?:OS|PFS|生存(?:期|时间)?)?|"
    r"有效率|响应率"
    r")"
    r"[^\n]{0,24}?"
    r"(?:\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:months?|mo\b|个?月|years?|年)|HR\s*[=:]?\s*\d|\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# A bare efficacy percentage anchored to a response/survival context word.
_BARE_EFFICACY_PCT_RE = re.compile(
    r"\d{1,3}(?:\.\d+)?\s*%[^\n]{0,24}?"
    r"(?:response|缓解|有效|survival|生存|control|控制|remission|ORR|DCR|PFS|OS)",
    re.IGNORECASE,
)
# A drug + explicit dose string (e.g. "adagrasib 600 mg BID", "顺铂 75 mg/m2").
# We key off the dose unit token; a bare lab number like "肌酐 88" has no dose
# unit so it is left to G35, not flagged here.
_DOSE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*"
    r"(?:mg|µg|ug|mcg|g|mL|ml|IU|U)"
    r"(?:\s*/\s*(?:m2|m²|kg|day|d|次|日))?"
    r"(?:\s*(?:BID|TID|QD|QW|Q2W|Q3W|QOD|每[日天周]|每\s*\d+\s*[日天周]|po|iv|ivgtt))?",
    re.IGNORECASE,
)

# Honest-uncertainty / properly-labelled tokens that must NOT be flagged as
# fabrication: an explicitly tier-labelled or source-anchored line is fine.
_ANCHORED_RE = re.compile(
    r"\[\[src:|\[PMID\s*:?\s*\d|\bNCT\d{8}\b|"
    r"\[(?:established|exploratory|speculative|已确立|探索性?|推测性?)\]|"
    r"参见来源|见来源|来源[:：]",
    re.IGNORECASE,
)
_BACKGROUND_TAG = re.compile(r"\[BACKGROUND\]", re.IGNORECASE)


def scan_brief_fabrication(
    text: str,
    *,
    gated_pmids: set[str] | None = None,
) -> list[FakeryFinding]:
    """Flag confident-but-unanchored fabrication signals in a delivered brief.

    Fires on a line that asserts an efficacy/response/survival number or a
    drug+dose string but carries NO anchor (no [[src:]], no [PMID:], no NCT,
    no tier label). Lines already anchored to a gated PMID/source are exempt
    (they are the *correct* shape). [BACKGROUND] prose is exempt.

    Conservative by design (flag-for-review): the returned findings tell the
    caller "this line states a clinical number with nothing behind it". The
    caller decides whether that hard-blocks (see delivery_gate_runner).
    """
    findings: list[FakeryFinding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or _BACKGROUND_TAG.search(stripped):
            continue
        if _ANCHORED_RE.search(stripped):
            continue  # the line carries provenance — not the fabrication shape
        is_efficacy = bool(_EFFICACY_RE.search(stripped) or _BARE_EFFICACY_PCT_RE.search(stripped))
        # drug+dose: a dose token present on the line (drug name is implied by
        # the dose unit; bare "88" labs are handled by G35, not here).
        is_drug_dose = bool(_DOSE_RE.search(stripped))
        if is_efficacy or is_drug_dose:
            kind = "unanchored_efficacy" if is_efficacy else "unanchored_drug_dose"
            findings.append(FakeryFinding(
                excerpt=stripped[:200],
                pattern=kind,
                line_number=i,
            ))
    return findings


def scan_brief_artifact(
    path: Path, *, gated_pmids: set[str] | None = None
) -> list[FakeryFinding]:
    """Scan a delivered brief file for unanchored fabrication signals."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return scan_brief_fabrication(text, gated_pmids=gated_pmids)
