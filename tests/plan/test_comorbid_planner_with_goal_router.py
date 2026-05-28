"""v2.1 P0-#4: comorbid_planner invokes goal_router before expansion returns."""
from __future__ import annotations

from opl_cancer.plan.comorbid_planner import maybe_expand_for_comorbid
from opl_cancer.plan.schemas import Task


def _baseline_tasks() -> list[Task]:
    return [
        Task(id="t1", expert="rosa", task_package="pathology_interpretation", sub_goal="x"),
        Task(id="t2", expert="bert", task_package="molecular_ngs_interpretation", sub_goal="x"),
        Task(id="t3", expert="rick", task_package="trial_matching", sub_goal="x"),
    ]


def test_vaccine_goal_adds_routed_experts_and_logs():
    """When the goal contains vaccine|neoantigen|TCR-T, tyler / julius / maya
    (etc) get added on top of any comorbid expansion."""
    profile: dict = {"prior_therapy_lines": 1, "concurrent_medications": [], "egfr_ml_min": 90}
    tasks, fired = maybe_expand_for_comorbid(
        _baseline_tasks(),
        profile,
        goal="Personalized neoantigen vaccine after L4 progression",
    )
    assigned_experts = {t.expert for t in tasks}
    assert {"tyler", "julius", "maya"} <= assigned_experts
    fired_names = {t.name for t in fired}
    # The router fires emit a trigger whose name is "goal_router:<pattern>"
    assert any(name.startswith("goal_router:") for name in fired_names)


def test_no_goal_text_keeps_baseline_behavior():
    """Calling without goal must still work (backward-compat)."""
    profile: dict = {"prior_therapy_lines": 1, "concurrent_medications": [], "egfr_ml_min": 90}
    tasks, fired = maybe_expand_for_comorbid(_baseline_tasks(), profile)
    # baseline + nothing else
    assert len(tasks) >= 3
    assert all(not t.name.startswith("goal_router:") for t in fired)
