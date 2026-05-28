"""v2.1 P0-#4: goal-keyword routing to experts."""
from __future__ import annotations

from opl_cancer.plan.goal_router import route_goal


def test_vaccine_goal_fires_tyler_frances_maya_julius_mark():
    experts = route_goal("Patient wants personalized TCR-T vaccine after L4 progression.")
    assert set(experts) >= {"tyler", "frances", "maya", "julius", "mark"}


def test_irae_goal_fires_mark_mary():
    experts = route_goal("Recurrent grade 2 endocrine_AE requires rechallenge plan.")
    assert set(experts) >= {"mark", "mary"}


def test_no_match_returns_empty():
    experts = route_goal("Just a routine staging update.")
    assert experts == []


def test_cross_border_fires_dennis_frances():
    experts = route_goal("Patient asks about cross_border treatment + expanded_access.")
    assert set(experts) >= {"dennis", "frances"}


def test_ctdna_fires_bert_aviv():
    experts = route_goal("Monitoring with ctDNA / MRD post-resection.")
    assert set(experts) >= {"bert", "aviv"}
