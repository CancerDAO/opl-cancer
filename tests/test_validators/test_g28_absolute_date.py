"""Tests for G28 absolute_date gate (v2.2 P1-#15).

Relative date language ("5 weeks ago", "approximately 3 months back", "X mo
ago") MUST carry an explicit `from_date`/`to_date` pair on the claim — or be
tagged `[BACKGROUND]`. Otherwise FAIL + block. This is the v2.1 LLM-confused-
weeks-for-months failure mode permanently closed at the mechanical layer.
"""
from __future__ import annotations

from opl_cancer.validators.gates.g28_absolute_date import G28AbsoluteDateGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g28_pass_when_no_relative_date() -> None:
    """Claim with only absolute dates → PASS."""
    gate = G28AbsoluteDateGate()
    claim = {
        "claim": "Patient initiated osimertinib on 2024-09-10.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g28_pass_when_relative_date_anchored() -> None:
    """Relative phrase but `from_date`/`to_date` present → PASS."""
    gate = G28AbsoluteDateGate()
    claim = {
        "claim": "ctDNA fell 5 weeks after C2D1.",
        "from_date": "2024-10-01",
        "to_date": "2024-11-05",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g28_fail_when_relative_date_without_anchor() -> None:
    """`5 weeks ago` without anchor → FAIL + block."""
    gate = G28AbsoluteDateGate()
    claim = {
        "claim": "Tumor markers fell 5 weeks ago.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "5 weeks" in r.message or "weeks" in r.message


def test_g28_fail_on_months_ago() -> None:
    gate = G28AbsoluteDateGate()
    claim = {"claim": "Diagnosed approximately 3 months ago.", "evidence": []}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g28_fail_on_x_mo_ago() -> None:
    """The original v2.1 failure mode — `5 mo ago` LLM-confused for `5 weeks`."""
    gate = G28AbsoluteDateGate()
    claim = {"claim": "Started pembrolizumab 5 mo ago.", "evidence": []}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL


def test_g28_skip_when_background_tagged() -> None:
    """[BACKGROUND] prose exempt — informational context isn't a clinical claim."""
    gate = G28AbsoluteDateGate()
    claim = {
        "claim": "[BACKGROUND] FDA approved pembrolizumab about 10 years ago.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP


def test_g28_pass_on_days_ago_with_anchor() -> None:
    gate = G28AbsoluteDateGate()
    claim = {
        "claim": "Lab drawn 3 days ago, ALT 220.",
        "from_date": "2026-05-22",
        "to_date": "2026-05-25",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g28_handles_chinese_relative_date() -> None:
    """Chinese 几周前/几个月前 patterns should also FAIL without anchor."""
    gate = G28AbsoluteDateGate()
    claim = {"claim": "三个月前开始仑伐替尼。", "evidence": []}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL


def test_g28_handles_empty_claim() -> None:
    gate = G28AbsoluteDateGate()
    r = gate.check({"claim": "", "evidence": []})
    assert r.status == GateStatus.PASS
