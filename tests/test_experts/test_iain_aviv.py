"""P2-T3+T4: IainExpert + AvivExpert."""
from __future__ import annotations

from typing import Any

from opl_cancer.experts.aviv import AvivExpert
from opl_cancer.experts.iain import IainExpert
from opl_cancer.experts.roster import get_expert_profile


class _NullClient:
    provider = "null"

    async def complete(self, request: Any) -> Any:  # pragma: no cover
        raise NotImplementedError


def _make_iain() -> IainExpert:
    return IainExpert(
        profile=get_expert_profile("iain"),
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def _make_aviv() -> AvivExpert:
    return AvivExpert(
        profile=get_expert_profile("aviv"),
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def test_iain_handles_meta_analysis() -> None:
    exp = _make_iain()
    assert exp.can_handle("meta_analysis")
    assert exp.can_handle("cross_source_consistency")
    assert not exp.can_handle("molecular_ngs_interpretation")


def test_iain_preferred_families() -> None:
    exp = _make_iain()
    assert "F1" in exp.preferred_families
    assert "F4" in exp.preferred_families


def test_iain_profile_name() -> None:
    exp = _make_iain()
    assert exp.profile.name == "iain"


def test_aviv_handles_hypothesis_generation() -> None:
    exp = _make_aviv()
    assert exp.can_handle("hypothesis_generation")
    assert exp.can_handle("pathway_enrichment")
    assert exp.can_handle("single_cell_reanalysis")
    assert not exp.can_handle("trial_matching")


def test_aviv_preferred_families() -> None:
    exp = _make_aviv()
    assert "F1" in exp.preferred_families
    assert "F6" in exp.preferred_families


def test_aviv_profile_name() -> None:
    exp = _make_aviv()
    assert exp.profile.name == "aviv"


def test_iain_in_roster() -> None:
    p = get_expert_profile("iain")
    assert p.name == "iain"
    assert "Chalmers" in p.inspiration


def test_aviv_in_roster() -> None:
    p = get_expert_profile("aviv")
    assert p.name == "aviv"
    assert "Regev" in p.inspiration
