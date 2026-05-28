"""Tests for v2.2 P1-#10 calibration-provenance helper in wave3_runner."""
from __future__ import annotations

import pytest

from opl_cancer.glue.wave3_runner import record_monte_carlo_calibration


def test_paper_derived_when_quote_is_point_value() -> None:
    rec = record_monte_carlo_calibration(
        parameter_name="lambda",
        value=0.55,
        extracted_quote="ctDNA decay rate constant lambda = 0.55/week (per Chen 2024)",
        was_from_full_text=True,
        pmid_anchor="38123456",
    )
    assert rec["parameter_calibration"] == "paper_derived"
    assert rec["value"] == 0.55
    assert rec["pmid_anchor"] == "38123456"


def test_informed_estimate_when_quote_is_range() -> None:
    rec = record_monte_carlo_calibration(
        parameter_name="lambda",
        value=0.55,
        extracted_quote="reported lambda range 0.42-0.71/week (95% CI)",
        was_from_full_text=True,
        pmid_anchor="38123456",
    )
    assert rec["parameter_calibration"] == "informed_estimate"


def test_literature_default_when_no_extraction() -> None:
    rec = record_monte_carlo_calibration(
        parameter_name="lambda",
        value=0.50,
        extracted_quote=None,
        was_from_full_text=False,
        used_default=True,
        pmid_anchor="canonical_default",
    )
    assert rec["parameter_calibration"] == "literature_default"


def test_raises_when_no_provenance_path_taken() -> None:
    with pytest.raises(ValueError):
        record_monte_carlo_calibration(
            parameter_name="lambda",
            value=0.50,
            extracted_quote=None,
            was_from_full_text=False,
            used_default=False,
        )
