"""Tests for v2.5 intake_router — RFC 0001 §8 item 8.

The session-c3195b66 regression test is the **release gating** test for v2.5.
"""
from __future__ import annotations

from opl_cancer.plan.intake_router import IntakeRoute, route_intake


# ─── session-c3195b66 regression (release-gating) ──────────────────────────


C3195B66_QUESTION = (
    "你会自动下载相关的公共数据库，并进行机器学习建模，"
    "找到最优的模型和参数，然后预测我的预后么"
)


def test_c3195b66_automl_prognosis_routes_to_unknown_task_intake() -> None:
    """RELEASE-GATING: the literal session-c3195b66 question must route to
    `unknown_task_intake` and emit a composed DAG that includes conformal
    + KM — NOT a flat refusal."""
    route = route_intake(C3195B66_QUESTION, profile={})
    assert isinstance(route, IntakeRoute)
    assert route.matched_task_package == "unknown_task_intake"
    dag_ids = {m["id"] for m in route.method_dag}
    # The router must surface conformal_prediction (uncertainty in N=1) and
    # kaplan_meier (prognosis baseline) as relevant primitives.
    assert "conformal_prediction" in dag_ids, (
        f"conformal_prediction not in DAG; got {dag_ids}"
    )
    assert "kaplan_meier" in dag_ids, f"kaplan_meier not in DAG; got {dag_ids}"
    # Must include an L4 disclosure card
    assert route.l4_disclosure_card is not None
    assert "AutoML" in route.l4_disclosure_card or "N=1" in route.l4_disclosure_card


def test_c3195b66_route_includes_acknowledgement_and_reasons() -> None:
    """The route must surface (a) acknowledgement, (b) decline reasons,
    (c) composed DAG. This is the heart of the bug-fix — no flat refusal."""
    route = route_intake(C3195B66_QUESTION, profile={})
    assert route.acknowledgement
    assert route.decline_reasons, "must surface reasons not 'we can't do this'"
    # at least one reason should reference N=1 or AutoML risk
    joined = " ".join(route.decline_reasons).lower()
    assert ("n=1" in joined) or ("automl" in joined) or ("overfitting" in joined)


# ─── known-task routing ────────────────────────────────────────────────────


def test_known_question_routes_to_task_package() -> None:
    """A question that maps to an existing task package goes there, not to
    unknown_task_intake."""
    route = route_intake(
        "please run an ACMG classification on the germline BRCA2 variant",
        profile={"cancer_type": "ovarian"},
    )
    # Should match the v2.2 ACMG task package directly.
    assert route.matched_task_package == "acmg_germline_classification"
    assert route.method_dag, "method_dag should still surface the method primitive"


def test_unknown_task_intake_md_file_shipped() -> None:
    """The new prompts/tasks/unknown_task_intake.md is shipped + non-empty."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    path = repo_root / "prompts" / "tasks" / "unknown_task_intake.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    # The prompt must address all 4 RFC parts: acknowledge / decline reasons /
    # method DAG / L4 disclosure card
    for token in ("Acknowledge", "Decline", "method DAG", "L4"):
        assert token in text or token.lower() in text.lower(), (
            f"{token!r} missing from unknown_task_intake.md"
        )


def test_intake_route_dataclass_serialization() -> None:
    route = route_intake(C3195B66_QUESTION, profile={})
    payload = route.to_dict()
    assert payload["matched_task_package"] == "unknown_task_intake"
    assert isinstance(payload["method_dag"], list)
    assert payload["l4_disclosure_card"]


def test_empty_question_routes_to_unknown_intake_without_crashing() -> None:
    route = route_intake("", profile={})
    # Empty input is treated like an unknown task — never an exception.
    assert route.matched_task_package == "unknown_task_intake"
