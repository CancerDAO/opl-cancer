"""P4-T8: Expert Batch D — Mary / Ted / Riad / Jen / Frances / Steve.

Verifies: portfolio + preferred_families + persona file + persona discipline.
Kieren / Mark / Dennis deferred to P4.5 (see plan + CHANGELOG).
"""
from __future__ import annotations

from typing import Any

import pytest

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.frances import FrancesExpert
from opl_cancer.experts.jen import JenExpert
from opl_cancer.experts.mary import MaryExpert
from opl_cancer.experts.riad import RiadExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.experts.steve import SteveExpert
from opl_cancer.experts.ted import TedExpert


class _NullClient:
    provider = "null"

    async def complete(self, request: Any) -> Any:  # pragma: no cover — never called
        raise NotImplementedError


_BATCH_D: tuple[type[LLMBackedExpert], ...] = (
    MaryExpert,
    TedExpert,
    RiadExpert,
    JenExpert,
    FrancesExpert,
    SteveExpert,
)


def _make(cls: type[LLMBackedExpert]) -> LLMBackedExpert:
    name = cls.__name__.lower().replace("expert", "")
    return cls(
        profile=get_expert_profile(name),
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


# ---- portfolios -------------------------------------------------------------


def test_mary_handles_ddi() -> None:
    exp = _make(MaryExpert)
    assert exp.can_handle("ddi_adme_dosing")
    assert exp.profile.name == "mary"
    assert "F10" in exp.preferred_families


def test_ted_handles_radiation_planning() -> None:
    exp = _make(TedExpert)
    assert exp.can_handle("radiation_planning")
    assert exp.profile.name == "ted"


def test_riad_handles_interventional() -> None:
    exp = _make(RiadExpert)
    assert exp.can_handle("interventional_oncology")
    assert exp.profile.name == "riad"


def test_jen_handles_palliative() -> None:
    exp = _make(JenExpert)
    assert exp.can_handle("palliative_symptom_qol")
    assert exp.profile.name == "jen"


def test_frances_handles_expanded_access() -> None:
    exp = _make(FrancesExpert)
    assert exp.can_handle("expanded_access_navigation")
    assert "F8" in exp.preferred_families
    assert exp.profile.name == "frances"


def test_steve_handles_nutrition() -> None:
    exp = _make(SteveExpert)
    assert exp.can_handle("oncology_nutrition")
    assert exp.profile.name == "steve"


# ---- persona files present + founder-mode discipline -----------------------


@pytest.mark.parametrize("cls", _BATCH_D)
def test_persona_file_exists(cls: type[LLMBackedExpert]) -> None:
    exp = _make(cls)
    p = exp._persona_path()
    assert p.exists(), f"{cls.__name__} persona missing at {p}"
    body = p.read_text(encoding="utf-8")
    assert "Anti-patterns" in body, f"{cls.__name__} persona missing Anti-patterns"
    assert "established" in body.lower(), (
        f"{cls.__name__} persona missing three-tier discipline"
    )


@pytest.mark.parametrize("cls", _BATCH_D)
def test_task_template_loadable(cls: type[LLMBackedExpert]) -> None:
    exp = _make(cls)
    for pkg in cls.portfolio:
        tmpl = exp._task_template(pkg)
        assert "JSON" in tmpl.source or "json" in tmpl.source, (
            f"{cls.__name__} task {pkg} missing JSON output rule"
        )


# ---- portfolio uniqueness across P1 + P3 + P4 ------------------------------


def test_batch_d_packages_disjoint_from_existing() -> None:
    """Batch D task packages must NOT collide with any existing expert's portfolio.

    Note: Aviv + Tyler legitimately share `hypothesis_validation` per P3 design
    (bioinformatician + wet-lab designer both contribute). We only enforce
    that Batch D introduces *new* task packages.
    """
    from opl_cancer.experts.aviv import AvivExpert
    from opl_cancer.experts.bert import BertExpert
    from opl_cancer.experts.heddy import HeddyExpert
    from opl_cancer.experts.hong import HongExpert
    from opl_cancer.experts.iain import IainExpert
    from opl_cancer.experts.rick import RickExpert
    from opl_cancer.experts.rosa import RosaExpert
    from opl_cancer.experts.tyler import TylerExpert
    from opl_cancer.experts.vince import VinceExpert

    existing: set[str] = set()
    for cls in (RosaExpert, BertExpert, VinceExpert, RickExpert, HeddyExpert,
                HongExpert, AvivExpert, IainExpert, TylerExpert):
        existing.update(cls.portfolio)

    batch_d_packages: set[str] = set()
    for cls in _BATCH_D:
        for pkg in cls.portfolio:
            assert pkg not in existing, (
                f"Batch D task {pkg!r} ({cls.__name__}) collides with existing expert"
            )
            assert pkg not in batch_d_packages, (
                f"Batch D internal collision on {pkg!r}"
            )
            batch_d_packages.add(pkg)

    assert batch_d_packages == {
        "ddi_adme_dosing",
        "radiation_planning",
        "interventional_oncology",
        "palliative_symptom_qol",
        "expanded_access_navigation",
        "oncology_nutrition",
    }


# ---- Frances special discipline (L4 boundary) ------------------------------


def test_frances_persona_forbids_guarantee_language() -> None:
    exp = _make(FrancesExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "guaranteed" in body.lower(), "Frances persona must explicitly forbid 'guaranteed'"
    assert "L4" in body or "boundary" in body.lower()


def test_frances_task_demands_l4_disclosure() -> None:
    exp = _make(FrancesExpert)
    tmpl = exp._task_template("expanded_access_navigation")
    assert "l4_boundary_disclosure" in tmpl.source
    assert "mandatory" in tmpl.source.lower()


# ---- Mary special (RxNorm anchor) ------------------------------------------


def test_mary_persona_demands_rxcui() -> None:
    exp = _make(MaryExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "rxcui" in body.lower()
    assert "TPMT" in body


# ---- Ted special (BED10 anchor) --------------------------------------------


def test_ted_persona_demands_bed10() -> None:
    exp = _make(TedExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "BED10" in body or "bed10" in body
    assert "OAR" in body


# ---- Riad special (Child-Pugh anchor) --------------------------------------


def test_riad_persona_demands_child_pugh() -> None:
    exp = _make(RiadExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "Child-Pugh" in body
    assert "BCLC" in body


# ---- Jen special (bowel regimen invariant) ---------------------------------


def test_jen_task_demands_bowel_regimen() -> None:
    exp = _make(JenExpert)
    tmpl = exp._task_template("palliative_symptom_qol")
    assert "bowel_regimen_present" in tmpl.source


# ---- Steve special (PG-SGA + ROS window) -----------------------------------


def test_steve_task_demands_pg_sga() -> None:
    exp = _make(SteveExpert)
    tmpl = exp._task_template("oncology_nutrition")
    assert "pg_sga" in tmpl.source.lower()
    assert "ros_window_caveat_required" in tmpl.source
