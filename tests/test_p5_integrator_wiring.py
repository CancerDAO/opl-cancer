"""P5 — Mary / Frances / Dennis / Rick can accept integrators dict via constructor.

Closes P4.5 deferred item: wire RxNorm to Mary; NMPA+FDA EAP to Frances; CT.gov+
ChiCTR to Dennis + Rick. The actual integrator instances are mocked here — the
test verifies the wiring contract (constructor accepts the dict, expert.integrate
routes by family).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from opl_cancer.experts.base import ExpertProfile
from opl_cancer.experts.dennis import DennisExpert
from opl_cancer.experts.frances import FrancesExpert
from opl_cancer.experts.mary import MaryExpert
from opl_cancer.experts.rick import RickExpert


def _profile(name: str) -> ExpertProfile:
    return ExpertProfile(
        name=name,
        role="test",
        inspiration="test",
        persona_summary="test",
        task_package_portfolio=[],
        preferred_integrator_families=[],
    )


def _mock_integrator(payload: dict[str, Any]) -> Any:
    m = AsyncMock()
    m.cached_fetch = AsyncMock(return_value=payload)
    return m


@pytest.mark.asyncio
async def test_mary_integrator_wiring_rxnorm() -> None:
    rxnorm = _mock_integrator({"rxcui": "1234", "name": "atezolizumab"})
    mary = MaryExpert(
        profile=_profile("mary"),
        executor_client=AsyncMock(),
        reviewer_client=AsyncMock(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F10": rxnorm},
    )
    out = await mary.integrate("F10", "atezolizumab")
    assert out["rxcui"] == "1234"


@pytest.mark.asyncio
async def test_frances_integrator_wiring_nmpa_fda_eap() -> None:
    nmpa = _mock_integrator({"protocol": "NMPA-EAP-001"})
    fda = _mock_integrator({"protocol": "FDA-EAP-002"})
    frances = FrancesExpert(
        profile=_profile("frances"),
        executor_client=AsyncMock(),
        reviewer_client=AsyncMock(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F8_nmpa": nmpa, "F8_fda": fda},
    )
    out_n = await frances.integrate("F8_nmpa", "drug-X")
    out_f = await frances.integrate("F8_fda", "drug-X")
    assert out_n["protocol"].startswith("NMPA")
    assert out_f["protocol"].startswith("FDA")


@pytest.mark.asyncio
async def test_dennis_integrator_wiring_ctgov_chictr() -> None:
    ctgov = _mock_integrator({"NCT": "NCT99999"})
    chictr = _mock_integrator({"ChiCTR": "ChiCTR-X-0001"})
    dennis = DennisExpert(
        profile=_profile("dennis"),
        executor_client=AsyncMock(),
        reviewer_client=AsyncMock(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F3_ctgov": ctgov, "F3_chictr": chictr},
    )
    out1 = await dennis.integrate("F3_ctgov", "lung+CN")
    out2 = await dennis.integrate("F3_chictr", "lung+CN")
    assert out1["NCT"].startswith("NCT")
    assert out2["ChiCTR"].startswith("ChiCTR")


@pytest.mark.asyncio
async def test_rick_integrator_wiring_ctgov_chictr() -> None:
    ctgov = _mock_integrator({"NCT": "NCT12345"})
    chictr = _mock_integrator({"ChiCTR": "ChiCTR-X-0002"})
    rick = RickExpert(
        profile=_profile("rick"),
        executor_client=AsyncMock(),
        reviewer_client=AsyncMock(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F3_ctgov": ctgov, "F3_chictr": chictr},
    )
    o1 = await rick.integrate("F3_ctgov", "HCC")
    o2 = await rick.integrate("F3_chictr", "HCC")
    assert o1["NCT"] == "NCT12345"
    assert o2["ChiCTR"] == "ChiCTR-X-0002"


@pytest.mark.asyncio
async def test_unknown_family_raises_keyerror() -> None:
    mary = MaryExpert(
        profile=_profile("mary"),
        executor_client=AsyncMock(),
        reviewer_client=AsyncMock(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F10": _mock_integrator({"x": 1})},
    )
    with pytest.raises(KeyError):
        await mary.integrate("F_nonexistent", "k")


def test_expert_portfolio_declared_after_p5() -> None:
    assert "ddi_adme_dosing" in MaryExpert.portfolio
    assert "expanded_access_navigation" in FrancesExpert.portfolio
    assert "cross_border_navigation" in DennisExpert.portfolio
    assert "trial_matching" in RickExpert.portfolio


def test_expert_preferred_families_declared() -> None:
    # F1+F10 for Mary, F3+F8 for the others.
    assert "F10" in MaryExpert.preferred_families
    assert "F3" in FrancesExpert.preferred_families
    assert "F3" in DennisExpert.preferred_families
    assert "F3" in RickExpert.preferred_families
