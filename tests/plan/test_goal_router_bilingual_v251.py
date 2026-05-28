"""v2.5.1 B4 — goal_router.yaml bilingual coverage + AutoML route.

Through v2.5.0 the patterns were English-only (`vaccine|neoantigen|TCR-T`);
Chinese-language patient questions never hit a keyword. v2.5.1 unifies
each entry with Chinese synonyms and adds a new AutoML / 预后预测 entry
for the c3195b66 case.
"""
from __future__ import annotations

import pytest

from opl_cancer.plan.goal_router import route_goal


@pytest.mark.parametrize(
    "chinese_goal,expected_subset",
    [
        ("个性化新抗原肿瘤疫苗", {"tyler", "frances", "maya", "julius", "mark"}),
        ("出现严重免疫相关不良反应，能否再激发", {"mark", "mary"}),
        ("想去海外就医，同情用药如何申请", {"dennis", "frances"}),
        ("肿瘤已经转移并出现耐药进展", {"bert", "julius", "maya"}),
        ("微卫星不稳定阳性 MSI-H", {"bert"}),
        ("肿瘤突变负荷 TMB 较高", {"bert"}),
        ("BRCA1 突变 + 同源重组缺陷", {"bert"}),
        ("胚系突变 + 家族史 BRCA2", {"bert"}),
        ("DPYD 药物基因组检测", {"mary"}),
        ("液体活检 ctDNA 微小残留", {"bert", "aviv"}),
    ],
)
def test_chinese_goals_fire_expected_experts(chinese_goal: str, expected_subset: set[str]) -> None:
    experts = route_goal(chinese_goal)
    assert set(experts) >= expected_subset, (chinese_goal, experts)


def test_automl_prognosis_chinese_routes_to_bert_aviv_iain() -> None:
    """B4 new keyword family — AutoML / prognostic-model / 机器学习建模 hits.

    These experts are the ones who can credibly answer the question
    (Bert: NGS/molecular; Aviv: bioinformatics; Iain: meta-analysis).
    Real routing to `unknown_task_intake` is intake_router's job; goal_router
    here just adds the right experts to the team.
    """
    experts = route_goal(
        "你能自动下载相关的公共数据库，并进行机器学习建模，找到最优的模型和参数，然后预测我的预后么"
    )
    assert set(experts) >= {"bert", "aviv", "iain"}, experts


def test_automl_english_route() -> None:
    experts = route_goal("Please build a prognostic model via AutoML using XGBoost")
    assert set(experts) >= {"bert", "aviv", "iain"}, experts


def test_english_goals_still_fire_after_bilingual_merge() -> None:
    """B4 regression — English patterns must keep working after bilingual merge."""
    assert set(route_goal("vaccine + neoantigen design")) >= {"tyler", "frances"}
    assert set(route_goal("irae rechallenge")) >= {"mark", "mary"}
    assert set(route_goal("cross_border expanded_access")) >= {"dennis", "frances"}
