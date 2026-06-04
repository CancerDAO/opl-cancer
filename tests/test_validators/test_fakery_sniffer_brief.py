"""v2.10 P0.3d: fakery sniffer flags confident-but-unanchored fabrication in a brief.

The placeholder sniffer (scan_text / scan_artifact) only catches a brief that
ADMITS it is unfinished (TODO / 待填充 / <insert PMID>). scan_brief_fabrication
catches the more dangerous shape the red-team reproduced: a brief that states a
confident efficacy number or a specific drug+dose with NO anchor behind it.
"""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.fakery_sniffer import (
    scan_brief_artifact,
    scan_brief_fabrication,
)


def test_flags_unanchored_efficacy_percentage() -> None:
    text = "The objective response rate (ORR) was 62% in this setting.\n"
    findings = scan_brief_fabrication(text)
    assert findings
    assert any(f.pattern == "unanchored_efficacy" for f in findings)


def test_flags_unanchored_median_os() -> None:
    text = "Median overall survival reached 14.2 months on this regimen.\n"
    findings = scan_brief_fabrication(text)
    assert any(f.pattern == "unanchored_efficacy" for f in findings)


def test_flags_unanchored_drug_dose() -> None:
    text = "Recommend adagrasib 600 mg BID with cetuximab.\n"
    findings = scan_brief_fabrication(text)
    assert any(f.pattern == "unanchored_drug_dose" for f in findings)


def test_efficacy_with_pmid_anchor_is_exempt() -> None:
    # a properly-cited efficacy number is the CORRECT shape — must not fire
    text = "ORR was 43% [PMID:36546659].\n"
    findings = scan_brief_fabrication(text)
    assert findings == []


def test_efficacy_with_src_anchor_is_exempt() -> None:
    text = "缓解率 53% [[src:ocr/trial.txt#L4]]\n"
    findings = scan_brief_fabrication(text)
    assert findings == []


def test_tier_labelled_line_is_exempt() -> None:
    text = "[speculative] ORR could be around 40% if the mechanism holds.\n"
    findings = scan_brief_fabrication(text)
    assert findings == []


def test_background_line_is_exempt() -> None:
    text = "[BACKGROUND] Roughly 30% of mCRC carries this alteration.\n"
    findings = scan_brief_fabrication(text)
    assert findings == []


def test_plain_prose_does_not_false_positive() -> None:
    text = (
        "This brief summarises research options for your situation.\n"
        "Your oncologist remains the sole decision authority.\n"
    )
    findings = scan_brief_fabrication(text)
    assert findings == []


def test_chinese_efficacy_flagged() -> None:
    text = "客观缓解率约为 62%。\n"
    findings = scan_brief_fabrication(text)
    assert any(f.pattern == "unanchored_efficacy" for f in findings)


def test_scan_brief_artifact_reads_file(tmp_path: Path) -> None:
    p = tmp_path / "patient_pi_brief.md"
    p.write_text("Recommend osimertinib 80 mg QD; ORR 71%.\n", encoding="utf-8")
    findings = scan_brief_artifact(p)
    assert findings
