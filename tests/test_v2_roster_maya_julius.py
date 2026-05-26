"""v2 paradigm tests — Maya + Julius added to roster + expert classes importable."""
from __future__ import annotations

from opl_cancer.experts.julius import JuliusExpert
from opl_cancer.experts.maya import MayaExpert
from opl_cancer.experts.roster import ROSTER, get_expert_profile


def test_maya_in_roster():
    assert "maya" in ROSTER
    p = get_expert_profile("maya")
    assert "synergy" in p.role.lower() or "knowledge-graph" in p.role.lower()


def test_julius_in_roster():
    assert "julius" in ROSTER
    p = get_expert_profile("julius")
    assert "chemist" in p.role.lower() or "medicinal" in p.role.lower()


def test_roster_has_20_experts():
    assert len(ROSTER) == 20


def test_maya_class_has_synergy_portfolio():
    assert "target_synergy_emergent" in MayaExpert.portfolio
    assert "synthetic_lethal_partner_query" in MayaExpert.portfolio


def test_julius_class_has_undrugged_design_portfolio():
    assert "undrugged_target_design" in JuliusExpert.portfolio
    assert "virtual_screen_design" in JuliusExpert.portfolio


def test_maya_julius_persona_version_v2():
    assert MayaExpert.persona_version == "v2.0.0"
    assert JuliusExpert.persona_version == "v2.0.0"
