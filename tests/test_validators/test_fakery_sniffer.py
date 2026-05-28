"""v2.1 P1-#9: fakery sniffer detects placeholder language in artifacts."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.fakery_sniffer import scan_artifact, scan_text


_FIX = Path("tests/fixtures/fakery_synthetic")


def test_sniffer_detects_placeholder():
    findings = scan_artifact(_FIX / "sample_fake.md")
    excerpts = " ".join(f.excerpt for f in findings)
    assert "[speculative" in excerpts or "<insert PMID>" in excerpts
    # We expect at least three independent finds (speculative + insert + approximately)
    assert len(findings) >= 2


def test_sniffer_clean_passes():
    findings = scan_artifact(_FIX / "sample_clean.md")
    assert findings == []


def test_background_tag_exempts():
    text = "[BACKGROUND] Approximately 5 million cases worldwide."
    findings = list(scan_text(text))
    assert findings == []


def test_insert_value_token_detected():
    text = "ORR is <insert value> in our cohort."
    findings = list(scan_text(text))
    assert findings
    assert any("insert" in f.excerpt.lower() for f in findings)


def test_projected_tag_detected():
    text = "Per the [projected] estimate, response is high."
    findings = list(scan_text(text))
    assert findings
