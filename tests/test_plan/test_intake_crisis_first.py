"""v2.6.0 — crisis detection (G24) must fire FIRST in route_intake.

Independent product review (2026-05-29) found G24CrisisDetectionGate is fully
implemented + unit-tested but NEVER invoked at runtime: a patient typing
self-harm language into the goal box is keyword-routed like any other question
(intake_router maps "crisis"/"suicide" to a task-package string but never scans
the actual text, and the real bilingual SI banks in g24 are never run). On the
wired path a suicidal patient could be routed to a trial-dump. The fix keeps the
gate MECHANICAL (per the gate's own design — an LLM cannot suppress it) and wires
it as the FIRST step of route_intake, ahead of all keyword routing.

These are the failing-first tests.
"""
from __future__ import annotations

import pytest

from opl_cancer.plan.intake_router import route_intake


@pytest.mark.parametrize(
    "goal",
    [
        "我活着真没意思，想结束这一切，三线还有什么药能试？",  # zh active-ish SI buried in a clinical question
        "I can't go on anymore. what trials are left for my mCRC?",  # en SI + a routable question
    ],
)
def test_crisis_overrides_all_routing(goal: str) -> None:
    route = route_intake(goal)
    # Crisis must win over the (otherwise routable) clinical question.
    assert route.matched_task_package == "crisis_card_emission", route
    assert getattr(route, "crisis_block", False) is True, route
    # The crisis evidence (grade + handoff + jurisdiction) must be surfaced.
    assert route.crisis_evidence, route
    assert "crisis_grade" in route.crisis_evidence
    # It must NOT have quietly attached an AutoML/KM speculative DAG.
    assert route.method_dag == [], route


def test_non_crisis_question_routes_normally() -> None:
    route = route_intake("我想做 TMB 计算")
    assert route.matched_task_package != "crisis_card_emission"
    assert getattr(route, "crisis_block", False) is False
