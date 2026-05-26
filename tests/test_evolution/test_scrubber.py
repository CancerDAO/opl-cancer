"""Scrubber tests — verify PHI strippers fire on realistic Chinese patient data."""
from __future__ import annotations

from opl_cancer.evolution.models import TraceDigest, WaveSummary
from opl_cancer.evolution.scrubber import _scrub_text, scrub


def test_scrub_strips_chinese_patient_name():
    out = _scrub_text("患者王国洪 69 岁男性")
    assert "王国洪" not in out
    assert "[NAME]" in out


def test_scrub_strips_dob_iso_date():
    out = _scrub_text("出生 1956-03-12 入院 2024-09-07")
    assert "1956-03-12" not in out
    assert "2024-09-07" not in out
    assert out.count("[DATE]") >= 2


def test_scrub_strips_chinese_id():
    out = _scrub_text("身份证 110101199003078888")
    assert "110101199003078888" not in out
    assert "[ID]" in out


def test_scrub_strips_pt_code():
    out = _scrub_text("Patient PT-EE62321353 referred")
    assert "PT-EE62321353" not in out
    assert "PT-[SCRUBBED]" in out


def test_scrub_strips_email():
    out = _scrub_text("Contact: dr.zhang@cancer-hospital.cn")
    assert "dr.zhang@cancer-hospital.cn" not in out
    assert "[EMAIL]" in out


def test_scrub_strips_chinese_hospital():
    out = _scrub_text("北京大学肿瘤医院 oncology")
    assert "肿瘤医院" not in out
    assert "[HOSPITAL]" in out


def test_scrub_preserves_gene_and_drug_names():
    # CRITICAL: scrubber must NOT strip the analytic substrate
    out = _scrub_text("KRAS G12C variant treated with sotorasib + cetuximab")
    assert "KRAS" in out
    assert "G12C" in out
    assert "sotorasib" in out
    assert "cetuximab" in out


def test_scrub_preserves_pmid_and_nct():
    out = _scrub_text("Per PMID 36546659 + NCT04185883 KRYSTAL-1 results")
    assert "36546659" in out
    assert "NCT04185883" in out


def test_scrub_digest_returns_new_object_with_marker():
    d = TraceDigest(
        run_id="run-x",
        patient_code_scrubbed="PT-EE62321353",  # pretend unscrubbed
        notable_issues=["患者王国洪 cardiac ambiguity"],
        waves=[WaveSummary(wave=2, errors=["error in 2024-09-07 record"])],
    )
    out = scrub(d)
    assert out.is_scrubbed() is True
    assert "王国洪" not in out.notable_issues[0]
    assert "2024-09-07" not in out.waves[0].errors[0]


# v2.0.1 (post-review) — additional PHI surfaces

def test_scrub_strips_pinyin_name():
    out = _scrub_text("Patient Zhang Wei (张伟) referred")
    assert "Zhang Wei" not in out
    assert "[NAME]" in out


def test_scrub_strips_pinyin_with_hyphen():
    out = _scrub_text("Dr. Li Xiao-Ming reviewed the case")
    assert "Li Xiao-Ming" not in out
    assert "[NAME]" in out


def test_scrub_strips_chinese_date_format():
    out = _scrub_text("入院 2026年5月27日 / 2026年5月")
    assert "2026年5月27日" not in out
    assert "2026年5月" not in out
    assert out.count("[DATE]") >= 1


def test_scrub_strips_mainland_mobile():
    out = _scrub_text("联系 13800138000 拒接")
    assert "13800138000" not in out
    assert "[PHONE]" in out


def test_scrub_strips_inpatient_number():
    out = _scrub_text("住院号 ZY20260012345 入院")
    assert "ZY20260012345" not in out
    assert "[MRN]" in out


def test_scrub_strips_huaxi_zhongshan_hospitals():
    """Top-tier hospital abbreviations (华西 / 中山 / 协和 / 瑞金) without 医院 suffix."""
    out = _scrub_text("会诊 华西医院 + 中山医院")
    assert "华西" not in out
    assert "中山" not in out
    assert "[HOSPITAL]" in out


def test_scrub_does_not_mutate_input():
    d = TraceDigest(
        run_id="run-x",
        notable_issues=["患者王国洪 alert"],
    )
    _ = scrub(d)
    # original untouched
    assert "王国洪" in d.notable_issues[0]
