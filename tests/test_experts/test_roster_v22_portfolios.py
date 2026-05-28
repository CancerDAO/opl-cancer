"""v2.2 ADR-0022 — roster portfolios populated for Bert / Aviv / Mary / Maya."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.experts.roster import ROSTER


PROMPTS_TASKS = Path(__file__).resolve().parents[2] / "prompts" / "tasks"


def test_roster_has_20_experts() -> None:
    assert len(ROSTER) == 20


def test_bert_portfolio_v22() -> None:
    bert = ROSTER["bert"]
    portfolio = bert.task_package_portfolio
    for pkg in (
        "msi_detection",
        "tmb_calculation",
        "cosmic_signature_extraction",
        "acmg_germline_classification",
    ):
        assert pkg in portfolio, f"bert missing {pkg}"


def test_aviv_portfolio_v22() -> None:
    aviv = ROSTER["aviv"]
    for pkg in ("biostats_survival", "biostats_subgroup"):
        assert pkg in aviv.task_package_portfolio


def test_mary_portfolio_v22() -> None:
    mary = ROSTER["mary"]
    assert "pharmacogenomics_cpic" in mary.task_package_portfolio


def test_maya_portfolio_v22() -> None:
    maya = ROSTER["maya"]
    assert "opentargets_evidence" in maya.task_package_portfolio


def test_every_portfolio_pkg_has_prompt_on_disk() -> None:
    """Every package named in a portfolio must correspond to a real
    prompts/tasks/<pkg>.md file. Catches typos at module-import time."""
    for name, profile in ROSTER.items():
        for pkg in profile.task_package_portfolio:
            p = PROMPTS_TASKS / f"{pkg}.md"
            assert p.exists(), f"expert {name} portfolio references missing prompt {p}"


def test_preferred_integrator_families_set_for_v22_experts() -> None:
    for name in ("bert", "aviv", "mary", "maya"):
        assert ROSTER[name].preferred_integrator_families, (
            f"v2.2 expert {name} must declare preferred_integrator_families"
        )
