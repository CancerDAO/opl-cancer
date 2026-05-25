"""Tests for v1.5 P1 group B artifacts.

Validates the structural contracts shipped in P1-B (stop-rules JSON,
CN-source mandate, min-N retrieval contract reference). The actual
prompt-level integration is asserted via the persona_prefix tests in
test_validators/test_g27_privacy_scrub.py::test_persona_prefix_file_present.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# ─── Shared clinical stop-rules JSON ────────────────────────────────────


def test_clinical_stop_rules_file_present() -> None:
    p = REPO_ROOT / "references" / "clinical_stop_rules.json"
    assert p.exists(), f"missing stop-rules JSON at {p}"


def test_clinical_stop_rules_schema_v15() -> None:
    p = REPO_ROOT / "references" / "clinical_stop_rules.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["_meta"]["schema"] == "clinical_stop_rules v1.5"
    assert "stop_rules" in payload
    assert isinstance(payload["stop_rules"], list)
    assert len(payload["stop_rules"]) >= 5


def test_clinical_stop_rules_each_has_required_keys() -> None:
    p = REPO_ROOT / "references" / "clinical_stop_rules.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    required = {"id", "trigger", "action_class", "affected_drugs", "evidence"}
    for rule in payload["stop_rules"]:
        missing = required - set(rule.keys())
        assert not missing, f"rule {rule.get('id', '?')} missing keys: {missing}"


def test_clinical_stop_rules_cover_canonical_organs() -> None:
    """v1.4 audit found eGFR / LVEF / ALB / active-irAE thresholds
    scattered across personas. v1.5 demands they're all in one place."""
    p = REPO_ROOT / "references" / "clinical_stop_rules.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    rule_ids = {r["id"] for r in payload["stop_rules"]}
    for canonical in (
        "STOP-RENAL-1",
        "STOP-CARDIAC-1",
        "STOP-HEPATIC-1",
        "STOP-ACTIVE-IRAE-1",
        "STOP-MARROW-1",
        "STOP-BLEED-1",
        "STOP-QTC-1",
    ):
        assert canonical in rule_ids, f"missing canonical rule {canonical}"


def test_clinical_stop_rules_evidence_pmid_or_named_source() -> None:
    p = REPO_ROOT / "references" / "clinical_stop_rules.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    for rule in payload["stop_rules"]:
        ev = rule["evidence"]
        assert isinstance(ev, list) and len(ev) > 0, f"{rule['id']} has empty evidence"
        # At least one entry should be a PMID, a guideline name, or a label
        recognized = any(
            "PMID" in e or "SmPC" in e or "guideline" in e.lower() or "label" in e.lower() or "ESMO" in e or "ASCO" in e
            for e in ev
        )
        assert recognized, f"{rule['id']} evidence not recognizable: {ev}"


# ─── CN-source mandate ───────────────────────────────────────────────────


def test_cn_source_mandate_file_present() -> None:
    p = REPO_ROOT / "prompts" / "safety" / "cn_source_mandate.md"
    assert p.exists()


def test_cn_source_mandate_lists_required_sources() -> None:
    p = REPO_ROOT / "prompts" / "safety" / "cn_source_mandate.md"
    content = p.read_text(encoding="utf-8")
    for required in (
        "NMPA",
        "国家医保局",
        "CSCO",
        "中华医学会",
        "ChiCTR",
        "Boao",
        "港澳药械通",
    ):
        assert required in content, f"missing CN source: {required}"


def test_cn_source_mandate_specifies_when_to_apply() -> None:
    p = REPO_ROOT / "prompts" / "safety" / "cn_source_mandate.md"
    content = p.read_text(encoding="utf-8")
    assert "profile.country" in content
    assert "mainland China" in content or "中国" in content


def test_cn_source_mandate_required_behavior_block() -> None:
    p = REPO_ROOT / "prompts" / "safety" / "cn_source_mandate.md"
    content = p.read_text(encoding="utf-8")
    assert "Required behavior" in content
    # Off-label regimen should surface 3 access channels
    assert "Boao" in content
    assert "EAP" in content
    assert "HK" in content or "GBA" in content


# ─── Persona prefix has retrieval + patient-anchor requirements ─────────


def test_persona_prefix_has_min_n_concept() -> None:
    """v1.5 P1-2: every persona's retrieval-summary footer should anchor
    on PMID counts — the prefix introduces the schema."""
    p = REPO_ROOT / "prompts" / "experts" / "_shared" / "persona_prefix.md"
    content = p.read_text(encoding="utf-8")
    # Tier-A claims require PMIDs; BACKGROUND-UNSOURCED is the explicit fallback
    assert "BACKGROUND-UNSOURCED" in content
    # Retrieval summary footer must enumerate PMID counts + verified date
    assert "PMIDs cited" in content
    assert "verified" in content.lower()
