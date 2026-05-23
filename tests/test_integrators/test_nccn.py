"""Test NCCNPageIndexIntegrator — local excerpts lookup."""
import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.nccn import NCCNPageIndexIntegrator


async def test_fetch_hcc_returns_decision_nodes() -> None:
    i = NCCNPageIndexIntegrator(cache=None)
    r = await i.fetch("HCC:BCLC stage C first-line")
    assert r["cancer_type"] == "HCC"
    assert r["version"].startswith("v3.2025")
    assert any("Atezolizumab" in n["excerpt"] for n in r["matches"])


async def test_fetch_nsclc_egfr() -> None:
    i = NCCNPageIndexIntegrator(cache=None)
    r = await i.fetch("NSCLC:EGFR osimertinib progression")
    assert any("amivantamab" in n["excerpt"].lower() for n in r["matches"])


async def test_fetch_unknown_cancer_raises() -> None:
    i = NCCNPageIndexIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("MELANOMA:advanced")


def test_family_is_F2() -> None:
    assert NCCNPageIndexIntegrator(cache=None).family == "F2"
