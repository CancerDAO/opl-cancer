"""Test 6 concrete experts: portfolio + integrator preferences set correctly.

Plan refs: P1-T26.

Each test instantiates the concrete expert with NO real LLM client (we only
exercise can_handle / class attributes / portfolio uniqueness here — actual
LLM call paths are exercised in test_common.py with mocked clients).
"""
from __future__ import annotations

from typing import Any

import pytest

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.bert import BertExpert
from opl_cancer.experts.heddy import HeddyExpert
from opl_cancer.experts.hong import HongExpert
from opl_cancer.experts.rick import RickExpert
from opl_cancer.experts.rosa import RosaExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.experts.vince import VinceExpert


class _NullClient:
    """Throw-away LLMClient stand-in for tests that only inspect class attrs."""

    provider = "null"

    async def complete(self, request: Any) -> Any:  # pragma: no cover — never called
        raise NotImplementedError


_ALL_EXPERTS: tuple[type[LLMBackedExpert], ...] = (
    RosaExpert,
    BertExpert,
    VinceExpert,
    RickExpert,
    HeddyExpert,
    HongExpert,
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


# ---- per-expert portfolio assertions ---------------------------------------


def test_rosa_handles_pathology() -> None:
    exp = _make(RosaExpert)
    assert exp.can_handle("pathology_interpretation")
    assert not exp.can_handle("molecular_ngs_interpretation")
    assert exp.profile.name == "rosa"


def test_bert_handles_ngs() -> None:
    exp = _make(BertExpert)
    assert exp.can_handle("molecular_ngs_interpretation")
    assert not exp.can_handle("pathology_interpretation")
    assert exp.profile.name == "bert"


def test_vince_handles_treatment_line() -> None:
    exp = _make(VinceExpert)
    assert exp.can_handle("treatment_line_recommendation")
    assert not exp.can_handle("trial_matching")
    assert exp.profile.name == "vince"


def test_rick_handles_trial_matching() -> None:
    exp = _make(RickExpert)
    assert exp.can_handle("trial_matching")
    assert not exp.can_handle("treatment_line_recommendation")
    assert exp.profile.name == "rick"


def test_heddy_handles_recist() -> None:
    exp = _make(HeddyExpert)
    assert exp.can_handle("recist_progression")
    assert not exp.can_handle("tcm_oncology")
    assert exp.profile.name == "heddy"


def test_hong_handles_tcm() -> None:
    exp = _make(HongExpert)
    assert exp.can_handle("tcm_oncology")
    assert not exp.can_handle("recist_progression")
    assert exp.profile.name == "hong"


# ---- portfolio invariants --------------------------------------------------


def test_no_overlap_in_portfolios() -> None:
    all_packages: list[str] = []
    for cls in _ALL_EXPERTS:
        all_packages.extend(cls.portfolio)
    assert len(all_packages) == len(set(all_packages)), (
        f"task package overlap detected: {all_packages}"
    )


def test_six_experts_cover_six_task_packages() -> None:
    """Each P1 expert claims exactly ONE task package (per plan §T26)."""
    for cls in _ALL_EXPERTS:
        assert len(cls.portfolio) == 1, f"{cls.__name__} portfolio size != 1"
    all_packages = {pkg for cls in _ALL_EXPERTS for pkg in cls.portfolio}
    assert all_packages == {
        "pathology_interpretation",
        "molecular_ngs_interpretation",
        "treatment_line_recommendation",
        "trial_matching",
        "recist_progression",
        "tcm_oncology",
    }


# ---- integrator family preferences per spec ---------------------------------


def test_integrator_preferences_per_spec() -> None:
    # Bert: OncoKB/CIViC/ClinVar/gnomAD + cBioPortal/GDC
    assert "F4" in BertExpert.preferred_families
    assert "F5" in BertExpert.preferred_families
    # Rick: CT.gov/ChiCTR + EAP
    assert "F3" in RickExpert.preferred_families
    assert "F8" in RickExpert.preferred_families
    # Vince: NCCN + PubMed
    assert "F2" in VinceExpert.preferred_families
    assert "F1" in VinceExpert.preferred_families
    # Rosa: F4 (marker context)
    assert "F4" in RosaExpert.preferred_families
    # Heddy + Hong: F1 (PubMed)
    assert "F1" in HeddyExpert.preferred_families
    assert "F1" in HongExpert.preferred_families


# ---- Hong special discipline (founder-mode TCM safety) ----------------------


def test_hong_persona_demands_non_replacement() -> None:
    """Hong's persona MUST embed the non-replacement-of-standard-care promise."""
    exp = _make(HongExpert)
    persona = exp._persona_path().read_text(encoding="utf-8")
    assert "non_replacement_of_standard_care" in persona
    assert "adjuvant" in persona.lower()


def test_hong_task_prompt_demands_non_replacement_field() -> None:
    """Hong's task package MUST demand the JSON output to include the marker."""
    exp = _make(HongExpert)
    tmpl = exp._task_template("tcm_oncology")
    assert "non_replacement_of_standard_care" in tmpl.source
    assert "drug_herb_interactions" in tmpl.source


# ---- founder-mode promise enforced in personas -----------------------------


def test_each_persona_embeds_founder_mode_promise() -> None:
    """Every persona must surface uncertainty + no-paternalism stance."""
    for cls in _ALL_EXPERTS:
        exp = _make(cls)
        persona = exp._persona_path().read_text(encoding="utf-8")
        assert "Anti-patterns" in persona, f"{cls.__name__} persona missing Anti-patterns"
        # three-tier discipline anchor
        assert "established" in persona.lower(), (
            f"{cls.__name__} persona missing three-tier discipline"
        )


# ---- each subclass IS-A LLMBackedExpert -------------------------------------


def test_each_expert_inherits_llm_backed() -> None:
    for cls in _ALL_EXPERTS:
        assert issubclass(cls, LLMBackedExpert)


# ---- ExpertProfile carries roster identity ---------------------------------


@pytest.mark.parametrize(
    "cls,expected_role_substr",
    [
        (RosaExpert, "Pathologist"),
        (BertExpert, "Geneticist"),
        (VinceExpert, "Oncologist"),
        (RickExpert, "Clinical Trial"),
        (HeddyExpert, "Radiologist"),
        (HongExpert, "TCM"),
    ],
)
def test_expert_role_matches_roster(
    cls: type[LLMBackedExpert], expected_role_substr: str
) -> None:
    exp = _make(cls)
    assert expected_role_substr in exp.profile.role
