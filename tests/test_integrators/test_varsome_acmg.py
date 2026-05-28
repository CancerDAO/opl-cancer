"""Tests for VarSome / ACMG germline classifier wrapper (v2.2 ADR-0022).

ACMG 2015 germline classification combines a set of pathogenicity criteria
(PVS1, PS1-4, PM1-6, PP1-5 / BA1, BS1-4, BP1-7) and tallies them via the
canonical decision table (PVS1 + 1 PS + 2 PM → Pathogenic, etc.). VarSome
exposes an API that runs the same logic.

In v2.2 we ship the decision-table logic deterministically + a thin wrapper.
ClinVar lookup is via an existing integrator (clinvar.py).
"""
from __future__ import annotations

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.varsome_acmg import (
    ACMG_CATEGORIES,
    AcmgGermlineIntegrator,
    classify_acmg,
)


def test_acmg_categories_present() -> None:
    """Standard ACMG 2015 categories present (P, LP, VUS, LB, B)."""
    assert "Pathogenic" in ACMG_CATEGORIES
    assert "Likely Pathogenic" in ACMG_CATEGORIES
    assert "VUS" in ACMG_CATEGORIES
    assert "Likely Benign" in ACMG_CATEGORIES
    assert "Benign" in ACMG_CATEGORIES


def test_classify_acmg_pathogenic_pvs1_plus_one_ps() -> None:
    """PVS1 + 1 PS → Pathogenic (ACMG decision table rule 1a)."""
    out = classify_acmg(criteria=["PVS1", "PS1"])
    assert out["classification"] == "Pathogenic"
    assert "PVS1" in out["matched_criteria"]


def test_classify_acmg_likely_pathogenic_one_ps_one_pm() -> None:
    """1 PS + 1 PM → Likely Pathogenic (decision table rule 2c)."""
    out = classify_acmg(criteria=["PS3", "PM2"])
    assert out["classification"] == "Likely Pathogenic"


def test_classify_acmg_vus_when_inconclusive() -> None:
    out = classify_acmg(criteria=["PP3"])
    assert out["classification"] == "VUS"


def test_classify_acmg_benign_ba1() -> None:
    """BA1 alone → Benign (stand-alone benign)."""
    out = classify_acmg(criteria=["BA1"])
    assert out["classification"] == "Benign"


def test_classify_acmg_likely_benign_bs1_bp1() -> None:
    out = classify_acmg(criteria=["BS1", "BP1"])
    assert out["classification"] == "Likely Benign"


def test_classify_acmg_conflicting_pathogenic_and_benign() -> None:
    """Both pathogenic and benign criteria → VUS (ACMG rule 5)."""
    out = classify_acmg(criteria=["PS1", "BS1"])
    assert out["classification"] == "VUS"
    assert out["conflict_flag"] is True


def test_classify_acmg_invalid_criterion_raises() -> None:
    with pytest.raises(ValueError):
        classify_acmg(criteria=["NOT-A-REAL-CRITERION"])


def test_integrator_key_format() -> None:
    integ = AcmgGermlineIntegrator(mock_mode=True)
    import asyncio
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("malformed"))


def test_integrator_mock_path() -> None:
    integ = AcmgGermlineIntegrator(
        mock_mode=True,
        mock_criteria=["PVS1", "PS1", "PM2"],
    )
    import asyncio
    out = asyncio.run(integ.fetch("variant:BRCA1:c.5266dupC"))
    assert out["classification"] == "Pathogenic"
    assert out["engine"] == "acmg-mock"
    assert out["gene"] == "BRCA1"
    assert out["variant"] == "c.5266dupC"


def test_integrator_family_and_ttl() -> None:
    integ = AcmgGermlineIntegrator(mock_mode=True)
    assert integ.family == "F_BIO"
    assert integ.ttl_seconds > 0
