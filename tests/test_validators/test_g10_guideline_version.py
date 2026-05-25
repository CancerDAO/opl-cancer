"""Test G10 guideline-version freshness gate."""
from datetime import date

from opl_cancer.validators.gates.g10_guideline_version import G10GuidelineVersionGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g10_pass_fresh_guideline() -> None:
    gate = G10GuidelineVersionGate(today=date(2026, 5, 25))
    claim = {
        "evidence": [
            {
                "type": "guideline",
                "id": "NCCN-HCC",
                "source": "NCCN",
                "version": "v3.2026",
                "date": "2026-02-01",
            }
        ]
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g10_fail_missing_version() -> None:
    gate = G10GuidelineVersionGate(today=date(2026, 5, 25))
    claim = {"evidence": [{"type": "guideline", "id": "NCCN-HCC", "source": "NCCN"}]}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g10_warn_when_stale() -> None:
    gate = G10GuidelineVersionGate(today=date(2026, 5, 25), stale_months=12)
    claim = {
        "evidence": [
            {
                "type": "guideline",
                "id": "NCCN-HCC",
                "source": "NCCN",
                "version": "v1.2024",
                "date": "2024-01-01",
            }
        ]
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN not BLOCK
    assert "stale" in r.evidence


def test_g10_skip_no_guidelines() -> None:
    gate = G10GuidelineVersionGate()
    r = gate.check({"evidence": [{"type": "pmid", "id": "1"}]})
    assert r.status == GateStatus.SKIP
