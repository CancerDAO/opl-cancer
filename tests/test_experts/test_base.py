"""Test Expert abstract base + roster of named archetypes.

v1.x: 18 archetypes. v2.0.0 (ADR-0010): +2 (maya, julius) → 20 total.
"""
import pytest

from opl_cancer.experts.base import Expert, ExpertProfile
from opl_cancer.experts.roster import ROSTER, get_expert_profile


def test_roster_contains_named_experts() -> None:
    # v2.0.0: 18 v1 + 2 v2 (maya, julius) = 20. See ADR-0010.
    assert len(ROSTER) == 20


def test_roster_all_lowercase_first_names() -> None:
    for name in ROSTER:
        assert name == name.lower()
        assert " " not in name


def test_roster_includes_canonical_v1_18_plus_v2_2() -> None:
    expected_v1 = {
        "rosa", "bert", "vince", "rick", "heddy", "mary", "aviv", "tyler",
        "iain", "ted", "riad", "jen", "kieren", "mark", "hong", "frances",
        "dennis", "steve",
    }
    expected_v2 = {"maya", "julius"}
    assert expected_v1.issubset(set(ROSTER.keys()))
    assert expected_v2.issubset(set(ROSTER.keys()))
    assert set(ROSTER.keys()) == expected_v1 | expected_v2


def test_get_expert_profile_returns_profile() -> None:
    p = get_expert_profile("bert")
    assert isinstance(p, ExpertProfile)
    assert p.name == "bert"
    assert "vogelstein" in p.inspiration.lower()
    assert len(p.task_package_portfolio) >= 0


def test_get_expert_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_expert_profile("alice")


def test_expert_base_is_abstract() -> None:
    with pytest.raises(TypeError):
        Expert()  # type: ignore[abstract]


def test_expert_abc_enforces_6_primitive_grammar_plus_can_handle() -> None:
    """Spec §2.2 inner grammar: Expert ABC must declare all 6 primitives + can_handle."""
    required = {"can_handle", "plan", "execute", "review", "audit", "integrate", "feedback"}
    actual = set(Expert.__abstractmethods__)
    assert required.issubset(actual), f"missing abstract methods: {required - actual}"
