"""Tests for CPIC pharmacogenomics wrapper (v2.2 ADR-0022 — optional skill).

CPIC (cpicpgx.org) is the canonical pharmacogene→drug→action guideline
authority. We ship a curated subset table covering DPYD / TPMT / UGT1A1 /
CYP2D6 plus the integrator key parser. Live lookup goes through cpicpgx.org
API in production; mock mode for tests.
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.cpic import (
    CPIC_TABLE,
    CpicIntegrator,
    lookup_cpic,
)


def test_cpic_table_covers_key_genes() -> None:
    """v2.2 must ship DPYD / TPMT / UGT1A1 / CYP2D6 / CYP2C19 entries."""
    for g in ("DPYD", "TPMT", "UGT1A1", "CYP2D6", "CYP2C19"):
        assert g in CPIC_TABLE, f"CPIC table missing {g}"


def test_lookup_cpic_dpyd_fluoropyrimidine() -> None:
    out = lookup_cpic(gene="DPYD", drug="fluorouracil", phenotype="Poor Metabolizer")
    assert out["recommendation_level"] in {"A", "B"}
    assert "avoid" in out["recommendation"].lower() or "reduce" in out["recommendation"].lower()
    assert out["gene"] == "DPYD"


def test_lookup_cpic_tpmt_thiopurine() -> None:
    out = lookup_cpic(gene="TPMT", drug="mercaptopurine", phenotype="Poor Metabolizer")
    assert "reduce" in out["recommendation"].lower() or "avoid" in out["recommendation"].lower()


def test_lookup_cpic_ugt1a1_irinotecan() -> None:
    out = lookup_cpic(gene="UGT1A1", drug="irinotecan", phenotype="Poor Metabolizer")
    assert out["recommendation_level"] in {"A", "B"}


def test_lookup_cpic_unknown_gene_raises() -> None:
    with pytest.raises(ValueError):
        lookup_cpic(gene="UNKNOWN_GENE", drug="fluorouracil", phenotype="Poor Metabolizer")


def test_lookup_cpic_unknown_drug_for_gene() -> None:
    with pytest.raises(ValueError):
        lookup_cpic(gene="DPYD", drug="aspirin", phenotype="Poor Metabolizer")


def test_integrator_key_format_required() -> None:
    integ = CpicIntegrator()
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("not-a-valid-key"))


def test_integrator_lookup_via_key() -> None:
    integ = CpicIntegrator()
    out = asyncio.run(integ.fetch("gene:DPYD:drug:fluorouracil:phenotype:Poor Metabolizer"))
    assert out["gene"] == "DPYD"
    assert out["drug"] == "fluorouracil"


def test_integrator_family_and_ttl() -> None:
    integ = CpicIntegrator()
    assert integ.family == "F_BIO"
    assert integ.ttl_seconds > 0
