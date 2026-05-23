"""P4.5-T6: Expert Batch E — Kieren / Mark / Dennis.

Verifies portfolio + preferred_families + persona file + persona discipline.
Dennis L4-boundary discipline (founder-mode) enforced.
"""
from __future__ import annotations

from typing import Any

import pytest

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.dennis import DennisExpert
from opl_cancer.experts.kieren import KierenExpert
from opl_cancer.experts.mark import MarkExpert
from opl_cancer.experts.roster import get_expert_profile


class _NullClient:
    provider = "null"

    async def complete(self, request: Any) -> Any:  # pragma: no cover
        raise NotImplementedError


_BATCH_E: tuple[type[LLMBackedExpert], ...] = (KierenExpert, MarkExpert, DennisExpert)


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


def test_kieren_handles_neutropenic_fever() -> None:
    exp = _make(KierenExpert)
    assert exp.can_handle("neutropenic_fever_management")
    assert exp.profile.name == "kieren"
    assert "F1" in exp.preferred_families
    assert "F8" in exp.preferred_families


def test_mark_handles_ici_endocrine_irae() -> None:
    exp = _make(MarkExpert)
    assert exp.can_handle("ici_endocrine_irae")
    assert exp.profile.name == "mark"


def test_dennis_handles_cross_border_navigation() -> None:
    exp = _make(DennisExpert)
    assert exp.can_handle("cross_border_navigation")
    assert "F3" in exp.preferred_families
    assert "F8" in exp.preferred_families
    assert exp.profile.name == "dennis"


# ---- persona files + three-tier discipline ---------------------------------


@pytest.mark.parametrize("cls", _BATCH_E)
def test_persona_file_exists(cls: type[LLMBackedExpert]) -> None:
    exp = _make(cls)
    p = exp._persona_path()
    assert p.exists(), f"{cls.__name__} persona missing at {p}"
    body = p.read_text(encoding="utf-8")
    assert "Anti-patterns" in body
    assert "established" in body.lower()


@pytest.mark.parametrize("cls", _BATCH_E)
def test_task_template_loadable(cls: type[LLMBackedExpert]) -> None:
    exp = _make(cls)
    for pkg in cls.portfolio:
        tmpl = exp._task_template(pkg)
        assert "JSON" in tmpl.source or "json" in tmpl.source


# ---- Kieren special (MASCC / IDSA / pseudomonal anchors) -------------------


def test_kieren_persona_demands_mascc_idsa() -> None:
    exp = _make(KierenExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "MASCC" in body
    assert "IDSA" in body
    assert "pseudomonal" in body.lower()


def test_kieren_task_demands_mascc_score() -> None:
    exp = _make(KierenExpert)
    tmpl = exp._task_template("neutropenic_fever_management")
    assert "mascc_score" in tmpl.source.lower()
    assert "pseudomonal_coverage" in tmpl.source


# ---- Mark special (CTCAE / ASCO + adrenal-axis safety check) ---------------


def test_mark_persona_demands_ctcae_and_adrenal_check() -> None:
    exp = _make(MarkExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "CTCAE" in body
    assert "ASCO" in body
    assert "adrenal" in body.lower()


def test_mark_task_demands_adrenal_axis_field() -> None:
    exp = _make(MarkExpert)
    tmpl = exp._task_template("ici_endocrine_irae")
    assert "adrenal_axis_checked" in tmpl.source
    assert "ici_hold_decision" in tmpl.source


# ---- Dennis L4 boundary (founder-mode discipline) --------------------------


def test_dennis_persona_forbids_guarantee_language() -> None:
    exp = _make(DennisExpert)
    body = exp._persona_path().read_text(encoding="utf-8")
    assert "guaranteed" in body.lower()
    assert "L4" in body or "boundary" in body.lower()
    assert "never markets" in body.lower() or "never market" in body.lower()


def test_dennis_task_demands_l4_disclosure() -> None:
    exp = _make(DennisExpert)
    tmpl = exp._task_template("cross_border_navigation")
    assert "l4_boundary_disclosure" in tmpl.source
    assert "mandatory" in tmpl.source.lower()
    assert "cost_model" in tmpl.source


def test_dennis_task_demands_cost_reality() -> None:
    exp = _make(DennisExpert)
    tmpl = exp._task_template("cross_border_navigation")
    assert "cost_estimate_usd_range" in tmpl.source
    assert "continuity_of_care_plan" in tmpl.source


# ---- portfolio uniqueness across all prior batches -------------------------


def test_batch_e_packages_disjoint_from_existing() -> None:
    from opl_cancer.experts.aviv import AvivExpert
    from opl_cancer.experts.bert import BertExpert
    from opl_cancer.experts.frances import FrancesExpert
    from opl_cancer.experts.heddy import HeddyExpert
    from opl_cancer.experts.hong import HongExpert
    from opl_cancer.experts.iain import IainExpert
    from opl_cancer.experts.jen import JenExpert
    from opl_cancer.experts.mary import MaryExpert
    from opl_cancer.experts.riad import RiadExpert
    from opl_cancer.experts.rick import RickExpert
    from opl_cancer.experts.rosa import RosaExpert
    from opl_cancer.experts.steve import SteveExpert
    from opl_cancer.experts.ted import TedExpert
    from opl_cancer.experts.tyler import TylerExpert
    from opl_cancer.experts.vince import VinceExpert

    existing: set[str] = set()
    for cls in (
        RosaExpert,
        BertExpert,
        VinceExpert,
        RickExpert,
        HeddyExpert,
        HongExpert,
        AvivExpert,
        IainExpert,
        TylerExpert,
        MaryExpert,
        TedExpert,
        RiadExpert,
        JenExpert,
        FrancesExpert,
        SteveExpert,
    ):
        existing.update(cls.portfolio)

    batch_e_packages: set[str] = set()
    for cls in _BATCH_E:
        for pkg in cls.portfolio:
            assert pkg not in existing, (
                f"Batch E task {pkg!r} ({cls.__name__}) collides with existing"
            )
            batch_e_packages.add(pkg)

    assert batch_e_packages == {
        "neutropenic_fever_management",
        "ici_endocrine_irae",
        "cross_border_navigation",
    }


# ---- Roster has all 18 experts now ----------------------------------------


def test_roster_complete_18_experts() -> None:
    from opl_cancer.experts.roster import ROSTER

    assert len(ROSTER) == 18
    for name in ("kieren", "mark", "dennis"):
        assert name in ROSTER
