"""Tests for patient_plain_brief_rendering task contract — v1.5 P0-4.

The actual rendered HTML output is tested by golden-set tests when the
renderer code lands. These tests validate the prompt + glossary contract
that the renderer will read.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_patient_plain_brief_task_prompt_exists() -> None:
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    assert p.exists(), f"missing task prompt at {p}"
    content = p.read_text(encoding="utf-8")
    assert "Plain-Language Translator" in content
    assert "delivery_audience" in content
    assert "lay" in content


def test_patient_plain_brief_has_4_mandatory_sections() -> None:
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    content = p.read_text(encoding="utf-8")
    # Each section heading appears (Chinese name + section number)
    assert "Section 1 · 你的病情一页纸" in content
    assert "Section 2 · 下一步要做什么" in content
    assert "Section 3 · 不同的选择" in content
    assert "Section 4 · 问医生的 5 个问题" in content


def test_patient_plain_brief_enforces_no_imperative_and_no_promises() -> None:
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    content = p.read_text(encoding="utf-8")
    # The prompt itself must call out the imperative + promise constraints.
    assert "G7" in content  # imperative gate
    assert "outcome promise" in content.lower() or "No outcome promises" in content


def test_patient_plain_brief_caps_length() -> None:
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    content = p.read_text(encoding="utf-8")
    # ≤ 2 pp constraint must be visible
    assert "2 sides" in content or "2 pp" in content or "≤ 2" in content


def test_patient_plain_brief_acknowledges_carried_forward_errors() -> None:
    """AP-12: v2 must not paper over v1 errors. Prompt must require honest
    disclosure of carried-forward errors in plain language."""
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    content = p.read_text(encoding="utf-8")
    assert "carried_forward_errors" in content
    assert "AP-12" in content


def test_patient_jargon_glossary_exists() -> None:
    p = REPO_ROOT / "references" / "patient_jargon_glossary.json"
    assert p.exists(), f"missing glossary at {p}"
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["_meta"]["schema"].startswith("patient_jargon_glossary")
    assert "terms" in payload


def test_patient_jargon_glossary_covers_v14_offenders() -> None:
    """The retro identified 60+ untranslated terms in v1.4. The glossary
    must cover the highest-frequency offenders so the renderer can resolve
    them on first use."""
    p = REPO_ROOT / "references" / "patient_jargon_glossary.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    must_have = [
        "KRAS",
        "KRAS G12C",
        "mCRC",
        "MSS",
        "ORR",
        "mPFS",
        "mOS",
        "ctDNA",
        "ADC",
        "ICI",
        "irAE",
        "log2FC",
        "I²",
        "LVEF",
        "eGFR",
        "CKD",
        "ECOG",
        "NCCN",
        "NMPA",
        "EAP",
        "RNF43",
        "TROP2",
    ]
    missing = [t for t in must_have if t not in payload["terms"]]
    assert not missing, f"glossary missing high-frequency v1.4 offenders: {missing}"


def test_patient_jargon_glossary_has_bilingual_entries() -> None:
    p = REPO_ROOT / "references" / "patient_jargon_glossary.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    for term, entry in payload["terms"].items():
        assert "zh" in entry, f"term {term!r} missing zh translation"
        assert "en" in entry, f"term {term!r} missing en translation"
        # Plain-language translations should be more than just a re-spelling.
        # 4-char Chinese (e.g. 慢性肾病) is fine; we just want non-trivial.
        assert len(entry["zh"]) >= 3, f"{term} zh translation too short"
        assert len(entry["en"]) >= 4, f"{term} en translation too short"
        # Must not be identical to the term itself (would be a trivial passthrough).
        assert entry["zh"] != term, f"{term} zh = term verbatim (no translation)"
        assert entry["en"] != term, f"{term} en = term verbatim (no translation)"


def test_patient_plain_brief_output_envelope_documented() -> None:
    """The prompt advertises an output JSON envelope; the renderer code
    will key on these field names. Make them stable."""
    p = REPO_ROOT / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
    content = p.read_text(encoding="utf-8")
    for required_field in [
        "task",
        "files_written",
        "gates_passed",
        "questions_for_doctor",
        "carried_forward_errors_acknowledged",
    ]:
        assert required_field in content, f"output schema field missing: {required_field}"
