"""Tests for COSMIC SigProfilerAssignment wrapper (v2.2 ADR-0022).

SigProfilerAssignment is heavy (downloads reference matrices on first run).
We test:
  * key parsing
  * mock mode returns the canonical {signatures, dominant_signature,
    interpretation} payload
  * live mode without SigProfilerAssignment installed raises IntegratorError
  * known-signature interpretation table is non-empty for SBS6 / SBS3 / SBS7a
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.cosmic_sigprofiler import (
    CosmicSigProfilerIntegrator,
    SBS_INTERPRETATION,
    interpret_signature,
)


def test_sbs_interpretation_table_populated() -> None:
    for sig in ("SBS1", "SBS3", "SBS6", "SBS7a", "SBS10a", "SBS18"):
        assert sig in SBS_INTERPRETATION
        assert SBS_INTERPRETATION[sig].get("etiology")


def test_interpret_signature_known() -> None:
    out = interpret_signature("SBS6")
    assert "mismatch_repair" in out["etiology"].lower() or "msi" in out["etiology"].lower()


def test_interpret_signature_unknown_returns_unannotated() -> None:
    out = interpret_signature("SBS999")
    assert out["etiology"]  # never empty
    assert "unannotated" in out["etiology"].lower() or "unknown" in out["etiology"].lower()


def test_integrator_mock_mode_returns_dominant_signature() -> None:
    integ = CosmicSigProfilerIntegrator(
        mock_mode=True,
        mock_signatures={"SBS6": 0.62, "SBS1": 0.18, "SBS5": 0.20},
    )
    out = asyncio.run(integ.fetch("vcf:/tmp/sample.vcf"))
    assert out["dominant_signature"] == "SBS6"
    assert abs(out["signatures"]["SBS6"] - 0.62) < 1e-6
    assert "mismatch_repair" in out["interpretation"]["etiology"].lower() or \
           "msi" in out["interpretation"]["etiology"].lower()
    assert out["engine"] == "sigprofiler-mock"


def test_integrator_key_format() -> None:
    integ = CosmicSigProfilerIntegrator(mock_mode=True, mock_signatures={"SBS1": 1.0})
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("not-a-vcf-key"))


def test_integrator_live_mode_without_dep_raises(monkeypatch) -> None:
    """Live mode requires SigProfilerAssignment importable. Stubbed absent."""
    integ = CosmicSigProfilerIntegrator(mock_mode=False)
    import sys
    # Ensure module is not imported
    monkeypatch.setitem(sys.modules, "SigProfilerAssignment", None)
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("vcf:/tmp/x.vcf"))


def test_integrator_normalises_signature_weights() -> None:
    """If mock weights don't sum to 1.0, integrator records the discrepancy."""
    integ = CosmicSigProfilerIntegrator(
        mock_mode=True,
        mock_signatures={"SBS3": 0.5, "SBS5": 0.2},
    )
    out = asyncio.run(integ.fetch("vcf:/tmp/sample.vcf"))
    assert out["signature_sum"] == pytest.approx(0.7)
    assert out["dominant_signature"] == "SBS3"
