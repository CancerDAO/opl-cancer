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
