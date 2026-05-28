"""Tests for paperqa_full_text integrator (v2.2 P1-#10).

P1-#10 — Monte Carlo λ for ctDNA decay in v2.1 was labeled "literature-
informed" without an extracted citation. v2.2 adds a full-text fetch shim
that records parameter calibration provenance as one of:
  * paper_derived       — value extracted from full-text quote
  * informed_estimate   — value bounded by literature range, exact extracted
  * literature_default  — fallback to a known canonical value with PMID

The integrator wraps PMC OA full-text fetch (PMID → PMC full-text URL via
ID-converter API). For unit tests we mock the HTTP layer.
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.paperqa_full_text import (
    CalibrationProvenance,
    PaperqaFullTextIntegrator,
    classify_calibration_provenance,
)


def test_classify_calibration_provenance_levels() -> None:
    assert classify_calibration_provenance(
        extracted_quote="lambda = 0.5/week", was_from_full_text=True
    ) == CalibrationProvenance.PAPER_DERIVED
    assert classify_calibration_provenance(
        extracted_quote="reported range 0.3-0.7/week", was_from_full_text=True
    ) == CalibrationProvenance.INFORMED_ESTIMATE
    assert classify_calibration_provenance(
        extracted_quote=None, was_from_full_text=False, used_default=True
    ) == CalibrationProvenance.LITERATURE_DEFAULT


def test_classify_raises_when_neither_provided() -> None:
    with pytest.raises(ValueError):
        classify_calibration_provenance(
            extracted_quote=None, was_from_full_text=False, used_default=False
        )


def test_integrator_fetch_full_text_via_pmid(monkeypatch) -> None:
    integ = PaperqaFullTextIntegrator()

    async def _fake_fetch_pmc(self, pmid: str) -> dict:
        assert pmid == "12345678"
        return {
            "pmid": pmid,
            "pmcid": "PMC9999999",
            "full_text": (
                "We modeled ctDNA decay as a single-compartment exponential with "
                "rate constant lambda = 0.55/week (95% CI 0.42-0.71)."
            ),
            "source": "pmc_oa",
        }

    monkeypatch.setattr(
        PaperqaFullTextIntegrator, "_fetch_pmc_full_text", _fake_fetch_pmc, raising=True
    )
    out = asyncio.run(integ.fetch("pmid:12345678"))
    assert out["pmid"] == "12345678"
    assert "lambda" in out["full_text"]
    assert out["pmcid"] == "PMC9999999"


def test_integrator_rejects_malformed_key() -> None:
    integ = PaperqaFullTextIntegrator()
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("not-a-pmid-key"))


def test_extract_numeric_parameter_with_quote() -> None:
    """The integrator helper finds `λ = 0.55/week` style numerics."""
    integ = PaperqaFullTextIntegrator()
    text = (
        "Methods. ctDNA half-life estimated at lambda = 0.55/week per Chen 2024 "
        "(95% CI 0.42-0.71)."
    )
    out = integ.extract_numeric_parameter(text=text, parameter_name="lambda")
    assert out["value"] == 0.55
    assert "Chen 2024" in out["quote"] or "lambda = 0.55" in out["quote"]


def test_extract_returns_none_when_not_found() -> None:
    integ = PaperqaFullTextIntegrator()
    out = integ.extract_numeric_parameter(
        text="No relevant rate constant discussed.", parameter_name="lambda"
    )
    assert out["value"] is None
    assert out["quote"] is None


def test_integrator_family_and_ttl() -> None:
    integ = PaperqaFullTextIntegrator()
    assert integ.family == "F1"  # PaperQA family
    assert integ.ttl_seconds > 0
