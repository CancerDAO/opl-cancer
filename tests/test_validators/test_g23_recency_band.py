"""Test G23 recency-band gate (v1.3.1 EVAL panel Patient #9 E4)."""
import datetime as _dt

from opl_cancer.validators.gates.g23_recency_band import G23RecencyBandGate
from opl_cancer.validators.mechanical_gates import GateStatus


_NOW = _dt.date(2026, 5, 25)


def test_g23_skip_topic_not_fast_moving() -> None:
    """Claim outside the fast-moving topic list → SKIP."""
    gate = G23RecencyBandGate(now=_NOW)
    claim = {
        "claim": "Adjuvant capecitabine in stage III colon cancer.",
        "evidence": [{"type": "pmid", "id": "11756428", "year": 2001}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP


def test_g23_pass_fast_moving_with_recent_pmid() -> None:
    """Fast-moving topic with recent PMID → PASS."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "Lu-177-PSMA-617 in mCRPC per VISION extension.",
        "evidence": [{"type": "pmid", "id": "39000000", "year": 2025}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g23_warn_fast_moving_with_stale_pmid() -> None:
    """Fast-moving topic with PMID > 18 mo → WARN (status FAIL, block False)."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "Lu-177-PSMA-617 cohort outcomes.",
        "evidence": [{"type": "pmid", "id": "33724867", "year": 2021}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN, never blocks
    assert "Lu-177".lower() in r.evidence["matched_topics"][0].lower() or any(
        "lu-177" in t for t in r.evidence["matched_topics"]
    )


def test_g23_warn_ar_v7_with_stale_pmid() -> None:
    """AR-V7 splice-variant topic with 2019 PMID → WARN."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "AR-V7 detection predicts ARSI resistance.",
        "evidence": [{"type": "pmid", "id": "31123456", "year": 2019}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert any("ar-v7" in t or "ar v7" in t for t in r.evidence["matched_topics"])


def test_g23_pub_date_string_recognised() -> None:
    """pub_date string (e.g. '2021 Jun') parsed correctly."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "KRAS G12C resistance to sotorasib.",
        "evidence": [{"type": "pmid", "id": "33999999", "pub_date": "2022 Mar"}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False


def test_g23_year_in_quote_fallback() -> None:
    """Last-resort year-in-quote regex hunt works."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "MET amplification post-osimertinib.",
        "evidence": [
            {"type": "pmid", "id": "31888888", "quote": "MET amp prevalence reported in 2020."}
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False


def test_g23_pass_when_no_evidence_year_known() -> None:
    """No year on any evidence → PASS (cannot determine staleness)."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "T-DXd post-DESTINY-Breast-06.",
        "evidence": [{"type": "pmid", "id": "39111111"}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g23_ignores_non_pmid_evidence_types() -> None:
    """Dataset evidence types are exempt from recency."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "PSMA-RLT cohort projection.",
        "evidence": [{"type": "dataset", "ref": "Hartwig-PCa", "year": 2019}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


# ─── v1.3.2 new fast-moving topics ─────────────────────────────────────────


def test_g23_detects_menin_inhibitor_topic() -> None:
    """v1.3.2: revumenib / menin inhibitor / KMT2A-r should fire fast-moving check."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "Revumenib in KMT2A-rearranged AML — pivotal AUGMENT-101 cohort.",
        "evidence": [{"type": "pmid", "id": "37000000", "year": 2022}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN
    matched = r.evidence["matched_topics"]
    assert any("menin" in t or "revumenib" in t or "kmt2a" in t for t in matched)


def test_g23_detects_ebv_ctl_topic() -> None:
    """v1.3.2: EBV-CTL / tabelecleucel / NPC should fire fast-moving check."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "Tabelecleucel (tab-cel) EBV-specific T cell therapy in NPC.",
        "evidence": [{"type": "pmid", "id": "36000000", "year": 2022}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    matched = r.evidence["matched_topics"]
    assert any("ebv" in t or "tab-cel" in t or "tabelecleucel" in t for t in matched)


def test_g23_detects_ha_wbrt_topic() -> None:
    """v1.3.2: HA-WBRT / hippocampal avoidance WBRT / NRG-CC003 should fire."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "HA-WBRT per NRG-CC003 protocol for brain metastases.",
        "evidence": [{"type": "pmid", "id": "34000000", "year": 2021}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    matched = r.evidence["matched_topics"]
    assert any("wbrt" in t or "cc003" in t for t in matched)


def test_g23_detects_kras_g12d_topic() -> None:
    """v1.3.2: KRAS G12D / MRTX1133 should fire fast-moving check."""
    gate = G23RecencyBandGate(recency_months=18, now=_NOW)
    claim = {
        "claim": "MRTX1133 (KRAS G12D inhibitor) preclinical → phase I.",
        "evidence": [{"type": "pmid", "id": "37500000", "year": 2023}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    matched = r.evidence["matched_topics"]
    assert any("kras" in t or "mrtx1133" in t for t in matched)
