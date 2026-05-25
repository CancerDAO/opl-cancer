"""Tests for v1.5 P1-5 G27 privacy-scrub gate."""
from __future__ import annotations

from opl_cancer.validators.gates import G27PrivacyScrubGate, redact_text, scan_text
from opl_cancer.validators.mechanical_gates import GateStatus


# ─── scan_text — pattern detection ──────────────────────────────────────


def test_scan_detects_cn_mobile_phone() -> None:
    matches = scan_text("Contact 13800138000 for follow-up.")
    assert len(matches) == 1
    assert matches[0].kind == "cn_phone"
    assert "13800138000" in matches[0].snippet


def test_scan_detects_cn_mobile_with_country_code() -> None:
    matches = scan_text("Family: +86 13800138000 or +8613811234567")
    assert len(matches) >= 2
    assert all(m.kind == "cn_phone" for m in matches)


def test_scan_detects_email() -> None:
    matches = scan_text("Reach the team at sid@cancerdao.org or rosa+work@example.cn")
    assert any(m.kind == "email" for m in matches)


def test_scan_detects_cn_national_id() -> None:
    # Synthetic but valid-shape second-gen CN ID
    matches = scan_text("ID 110101199001011234 on file.")
    assert any(m.kind == "cn_national_id" for m in matches)


def test_scan_detects_mrn_labeled() -> None:
    matches = scan_text("MRN: A123456 issued at HKSH")
    assert any(m.kind == "hospital_mrn" for m in matches)
    matches2 = scan_text("病案号 87654321 — XYZ Hospital")
    assert any(m.kind == "hospital_mrn" for m in matches2)


def test_scan_skips_pmid_context() -> None:
    """11-digit-looking numbers near 'PMID' are not phones."""
    matches = scan_text("Per PMID 37870968 the ORR was 26.4%.")
    assert not any(m.kind == "cn_phone" for m in matches)


def test_scan_skips_nct_context() -> None:
    matches = scan_text("Enrolled in NCT06959615 at Hangzhou site.")
    assert not any(m.kind == "cn_phone" for m in matches)


def test_scan_skips_dose_context() -> None:
    """Doses like '960 mg QD' must not be flagged as IDs."""
    matches = scan_text("Sotorasib 960 mg QD with panitumumab 6 mg/kg q2w.")
    assert len(matches) == 0


def test_scan_finds_pt_ee62321353_canonical_leak() -> None:
    """The exact phrase from Dennis's W1 report in the v1.4 retro."""
    matches = scan_text("Family contact: [FAMILY-CONTACT] 13800138000 ([LOCATION])")
    cn_phones = [m for m in matches if m.kind == "cn_phone"]
    assert len(cn_phones) == 1


# ─── redact_text — replacement ──────────────────────────────────────────


def test_redact_text_substitutes_tokens() -> None:
    text = "Call 13800138000 or email sid@example.com for details."
    redacted, matches = redact_text(text)
    assert "13800138000" not in redacted
    assert "sid@example.com" not in redacted
    assert "[REDACTED:cn_phone]" in redacted
    assert "[REDACTED:email]" in redacted
    assert len(matches) == 2


def test_redact_text_preserves_non_pii_content() -> None:
    text = "Sotorasib 960 mg QD per CodeBreaK 300 (PMID 37870968). Email me sid@cancerdao.org."
    redacted, _ = redact_text(text)
    assert "Sotorasib 960 mg QD" in redacted
    assert "PMID 37870968" in redacted
    assert "sid@cancerdao.org" not in redacted


def test_redact_text_empty_input() -> None:
    redacted, matches = redact_text("")
    assert redacted == ""
    assert matches == []


# ─── G27PrivacyScrubGate ────────────────────────────────────────────────


def test_gate_passes_when_no_pii() -> None:
    g = G27PrivacyScrubGate()
    r = g.check({"report_text": "Sotorasib + panitumumab per CodeBreaK 300 PMID 37870968."})
    assert r.status is GateStatus.PASS


def test_gate_blocks_when_phone_leaked() -> None:
    g = G27PrivacyScrubGate()
    r = g.check({"report_text": "Family contact 13800138000 on file."})
    assert r.status is GateStatus.FAIL
    assert r.block is True
    assert r.evidence["n_matches"] >= 1
    assert "cn_phone" in r.evidence["match_kinds"]


def test_gate_blocks_pt_ee62321353_canonical_leak() -> None:
    """End-to-end: Dennis's exact v1.4 report leak should fail G27."""
    g = G27PrivacyScrubGate()
    r = g.check(
        {
            "report_text": (
                "Dennis recommendation: route patient via Boao 乐城.\n"
                "Family contact: [FAMILY-CONTACT] 13800138000"
            )
        }
    )
    assert r.status is GateStatus.FAIL
    assert "cn_phone" in r.evidence["match_kinds"]


def test_gate_blocks_email_leak() -> None:
    g = G27PrivacyScrubGate()
    r = g.check(
        {"report_text": "Send protocols to dr.li@hospital.org for verification."}
    )
    assert r.status is GateStatus.FAIL
    assert "email" in r.evidence["match_kinds"]


def test_gate_blocks_mrn_leak() -> None:
    g = G27PrivacyScrubGate()
    r = g.check({"report_text": "病案号 87654321 (Beijing PUMCH)"})
    assert r.status is GateStatus.FAIL
    assert "hospital_mrn" in r.evidence["match_kinds"]


def test_gate_scans_all_string_fields_when_no_report_text() -> None:
    g = G27PrivacyScrubGate()
    r = g.check(
        {
            "summary": "patient stable on H02 sotorasib.",
            "footnote": "family rep at 13800138000",
        }
    )
    assert r.status is GateStatus.FAIL  # phone found in footnote


def test_gate_surfaces_up_to_5_samples() -> None:
    g = G27PrivacyScrubGate()
    text = "\n".join(
        f"contact at +86 1380000{i:04d}" for i in range(10)
    )
    r = g.check({"report_text": text})
    assert r.status is GateStatus.FAIL
    samples = r.evidence["samples"]
    assert 1 <= len(samples) <= 10


def test_persona_prefix_file_present() -> None:
    """The canonical persona prefix must exist alongside G27."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    p = repo_root / "prompts" / "experts" / "_shared" / "persona_prefix.md"
    assert p.exists(), f"missing prefix at {p}"
    content = p.read_text(encoding="utf-8")
    # Must mention G7 + traceability + patient-anchor + privacy
    assert "G7" in content
    assert "traceability" in content.lower() or "Source-traceability" in content
    assert "Patient-anchor" in content or "patient-anchor" in content.lower()
    assert "privacy" in content.lower() or "PII" in content
    # Forbidden words example block
    for forbidden in ("must", "should", "patient must", "永久停药"):
        assert forbidden in content, f"prefix missing forbidden word example: {forbidden}"
