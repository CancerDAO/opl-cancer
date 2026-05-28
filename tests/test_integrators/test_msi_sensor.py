"""Tests for MSIsensor wrapper (v2.2 ADR-0022).

`msi_sensor.py` is a thin deterministic wrapper around the canonical MSIsensor /
MSIsensor-pro CLI. Real execution requires samtools + MSIsensor binaries on
PATH and tumor+normal BAMs; in unit tests we exercise:
  * default disabled mode raises a clear IntegratorError when CLI missing
  * mock mode returns the canonical {msi_score, status, n_sites_examined,
    n_sites_unstable} payload
  * the result interpretation helper classifies scores correctly
  * key parsing rejects malformed inputs
"""
from __future__ import annotations

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.msi_sensor import (
    MSIsensorIntegrator,
    classify_msi_status,
)


def test_classify_msi_status_msih() -> None:
    out = classify_msi_status(msi_score=22.5)
    assert out["status"] == "MSI-H"
    assert out["msi_score"] == 22.5


def test_classify_msi_status_msil() -> None:
    out = classify_msi_status(msi_score=5.0)
    assert out["status"] == "MSI-L"


def test_classify_msi_status_mss() -> None:
    out = classify_msi_status(msi_score=1.2)
    assert out["status"] == "MSS"


def test_classify_msi_status_custom_thresholds() -> None:
    out = classify_msi_status(msi_score=15, msi_h_threshold=10.0, msi_l_threshold=3.0)
    assert out["status"] == "MSI-H"


def test_classify_msi_status_invalid() -> None:
    with pytest.raises(ValueError):
        classify_msi_status(msi_score=-1)


def test_integrator_key_format_rejects_malformed() -> None:
    integ = MSIsensorIntegrator(mock_mode=True)
    import asyncio
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("not-a-valid-key"))


def test_integrator_mock_mode_returns_msih_when_score_high() -> None:
    integ = MSIsensorIntegrator(mock_mode=True, mock_score=23.5, mock_sites=180)
    import asyncio
    out = asyncio.run(integ.fetch("tumor:/tmp/t.bam:normal:/tmp/n.bam"))
    assert out["msi_score"] == 23.5
    assert out["status"] == "MSI-H"
    assert out["n_sites_examined"] == 180
    assert out["engine"] == "msisensor-mock"
    assert "mock" in out["provenance"]


def test_integrator_mock_mode_returns_mss_when_low() -> None:
    integ = MSIsensorIntegrator(mock_mode=True, mock_score=1.1, mock_sites=200)
    import asyncio
    out = asyncio.run(integ.fetch("tumor:/tmp/t.bam:normal:/tmp/n.bam"))
    assert out["status"] == "MSS"


def test_integrator_live_mode_raises_when_binary_missing(monkeypatch) -> None:
    """Live mode (mock_mode=False) without msisensor binary on PATH must raise
    IntegratorError — never silently fall back (memory:feedback_no_offline_only)."""
    monkeypatch.setenv("PATH", "/nonexistent")
    integ = MSIsensorIntegrator(mock_mode=False)
    import asyncio
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("tumor:/tmp/t.bam:normal:/tmp/n.bam"))


def test_integrator_family_and_ttl() -> None:
    integ = MSIsensorIntegrator(mock_mode=True)
    assert integ.family == "F_BIO"
    # MSI status changes only with new sequencing; cache 30 days
    assert integ.ttl_seconds >= 7 * 24 * 3600
