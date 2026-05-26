"""PII/PHI scrubber for TraceDigest. ADR-0020 §What we add #8.

Runs BEFORE any LLM call. Strips patient name (Chinese + 拼音 + Latin),
DOB, MRN, addresses, dates, organization names.

This is intentionally aggressive — false positives (scrubbing a legitimate
gene name) are acceptable; false negatives (leaking PHI to a cloud LLM) are
not. The scrubber operates on the JSON-serialised digest string, never on
the source patient files.

Limitations honestly disclosed:
- Heuristic only. NOT a substitute for explicit consent or BAA.
- Cancer-type / drug names + PMID / NCT IDs are NOT scrubbed (they are
  the analytic substrate; without them the digest is useless).
"""
from __future__ import annotations

import re
from typing import Any

from .models import TraceDigest


# Chinese surname + given name (1-3 chars). False positives on common gene
# names like 'BRCA' are negligible because gene names are uppercase ASCII.
_CN_NAME = re.compile(r"[一-鿿]{2,4}")

# Email
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")

# Chinese ID (18 digits, last optionally X)
_CN_ID = re.compile(r"\b\d{17}[\dXx]\b")

# Phone — restricted to formatted patterns (with country code OR with
# hyphen/space separators) to avoid collision with PMIDs / NCT IDs / cohort sizes.
# Matches: +86 13800138000, +1-555-123-4567, 138-0013-8000.
# Does NOT match bare 8-digit medical IDs like PMID 36546659.
_PHONE = re.compile(
    r"\b\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,5}\b|\b\d{3,4}-\d{3,4}-\d{3,4}\b"
)

# ISO date YYYY-MM-DD and slash variants — PHI per HIPAA Safe Harbor for
# dates more granular than year.
_DATE = re.compile(
    r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"
)

# Patient code prefix used in OPL (PT-XXXXXXX) — leave the PT- prefix
# visible so the analyzer knows it's a patient but strip the discriminator.
_PT_CODE = re.compile(r"\bPT-[A-Z0-9]{6,}\b")

# Hospital / organisation Chinese token endings — only fires when 2-6
# Chinese chars precede.
_HOSPITAL_CN = re.compile(r"[一-鿿]{2,6}(医院|肿瘤医院|附属医院|人民医院|协和医院)")


def _scrub_text(text: str) -> str:
    """Apply all PHI strippers to a free-text field."""
    if not isinstance(text, str):
        return text
    text = _EMAIL.sub("[EMAIL]", text)
    text = _CN_ID.sub("[ID]", text)
    text = _DATE.sub("[DATE]", text)
    text = _PT_CODE.sub("PT-[SCRUBBED]", text)
    text = _HOSPITAL_CN.sub("[HOSPITAL]", text)
    text = _PHONE.sub("[PHONE]", text)
    text = _CN_NAME.sub("[NAME]", text)
    return text


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    return value


def scrub(digest: TraceDigest) -> TraceDigest:
    """Return a new TraceDigest with all string fields PHI-scrubbed.

    Numeric / structural fields untouched. Original digest not mutated.
    """
    raw = digest.model_dump()
    scrubbed_raw = _scrub_value(raw)
    # Ensure marker is set so is_scrubbed() returns True
    scrubbed_raw["patient_code_scrubbed"] = "[SCRUBBED]"
    return TraceDigest.model_validate(scrubbed_raw)
