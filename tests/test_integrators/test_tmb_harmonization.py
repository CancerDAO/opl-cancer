"""Tests for TMB harmonization integrator (v2.2 ADR-0022).

TMB (tumor mutational burden) is reported as mutations/Mb but panel-vendor
calculations diverge: TSO500 uses a 1.94-Mb effective territory; FoundationOne
uses 0.8-Mb; MSK-IMPACT-468 uses 1.22-Mb. The harmonization layer normalises
to the canonical 10/Mb (TMB-H FDA threshold per KEYNOTE-158).
"""
from __future__ import annotations

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.tmb_harmonization import (
    TMBHarmonizationIntegrator,
    classify_tmb_status,
    harmonize_tmb,
    PANEL_FOOTPRINTS_MB,
)


def test_panel_footprints_present() -> None:
    """Canonical panels — must be in the footprint map."""
    assert "TSO500" in PANEL_FOOTPRINTS_MB
    assert "FoundationOne" in PANEL_FOOTPRINTS_MB
    assert "MSK-IMPACT-468" in PANEL_FOOTPRINTS_MB
    assert "WES" in PANEL_FOOTPRINTS_MB
    for v in PANEL_FOOTPRINTS_MB.values():
        assert v > 0


def test_classify_tmb_status_high() -> None:
    out = classify_tmb_status(tmb_per_mb=15.0)
    assert out["status"] == "TMB-H"
    assert out["tmb_per_mb"] == 15.0


def test_classify_tmb_status_low() -> None:
    out = classify_tmb_status(tmb_per_mb=2.5)
    assert out["status"] == "TMB-L"


def test_classify_tmb_status_borderline() -> None:
    out = classify_tmb_status(tmb_per_mb=10.0)
    # Exactly 10 is TMB-H per KEYNOTE-158 cutoff
    assert out["status"] == "TMB-H"


def test_harmonize_tmb_from_raw_counts() -> None:
    """22 nonsynonymous mutations on TSO500 (1.94 Mb) → 11.34/Mb → TMB-H."""
    out = harmonize_tmb(n_mutations=22, panel="TSO500")
    assert abs(out["tmb_per_mb"] - 22 / 1.94) < 0.01
    assert out["status"] == "TMB-H"
    assert out["panel"] == "TSO500"
    assert out["effective_mb"] == 1.94


def test_harmonize_tmb_unknown_panel_raises() -> None:
    with pytest.raises(IntegratorError):
        harmonize_tmb(n_mutations=22, panel="UnknownVendor-X")


def test_harmonize_tmb_supports_direct_per_mb() -> None:
    """If a vendor reports already-normalized TMB, pass it through."""
    out = harmonize_tmb(tmb_per_mb=8.5, panel="FoundationOne")
    assert out["tmb_per_mb"] == 8.5
    assert out["status"] == "TMB-L"


def test_harmonize_requires_either_input() -> None:
    with pytest.raises(IntegratorError):
        harmonize_tmb(panel="TSO500")


def test_integrator_key_format() -> None:
    integ = TMBHarmonizationIntegrator()
    import asyncio
    out = asyncio.run(integ.fetch("panel:TSO500:n_mutations:22"))
    assert out["status"] == "TMB-H"


def test_integrator_supports_per_mb_key() -> None:
    integ = TMBHarmonizationIntegrator()
    import asyncio
    out = asyncio.run(integ.fetch("panel:FoundationOne:tmb_per_mb:12.3"))
    assert out["tmb_per_mb"] == 12.3
    assert out["status"] == "TMB-H"


def test_integrator_rejects_malformed_key() -> None:
    integ = TMBHarmonizationIntegrator()
    import asyncio
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("garbage"))


def test_integrator_family_and_ttl() -> None:
    integ = TMBHarmonizationIntegrator()
    assert integ.family == "F_BIO"
    assert integ.ttl_seconds > 0
