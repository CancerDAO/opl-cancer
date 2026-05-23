"""P3-T6: TylerExpert (Wet-Lab Designer)."""
from __future__ import annotations

from typing import Any

from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.experts.tyler import TylerExpert


class _NullClient:
    provider = "null"

    async def complete(self, request: Any) -> Any:  # pragma: no cover
        raise NotImplementedError


def _make_tyler() -> TylerExpert:
    return TylerExpert(
        profile=get_expert_profile("tyler"),
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def test_tyler_handles_hypothesis_validation() -> None:
    exp = _make_tyler()
    assert exp.can_handle("hypothesis_validation")
    assert exp.can_handle("in_silico_experiment_design")
    assert not exp.can_handle("meta_analysis")


def test_tyler_preferred_families() -> None:
    exp = _make_tyler()
    assert "F6" in exp.preferred_families
    assert "F7" in exp.preferred_families


def test_tyler_profile_name() -> None:
    exp = _make_tyler()
    assert exp.profile.name == "tyler"


def test_tyler_in_roster() -> None:
    p = get_expert_profile("tyler")
    assert p.name == "tyler"
    assert "Jacks" in p.inspiration


def test_aviv_extended_portfolio() -> None:
    from opl_cancer.experts.aviv import AvivExpert

    exp = AvivExpert(
        profile=get_expert_profile("aviv"),
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    assert exp.can_handle("dataset_acquisition")
    assert exp.can_handle("bioinformatics_data_analysis")
    assert "F7" in exp.preferred_families
