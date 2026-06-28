"""Tests for the de-scripted intake_router (ADR-0040).

Keyword task/method routing (_KNOWN_TASK_KEYWORDS + _UNKNOWN_DAG_STUBS) is removed
— that judgment now belongs to the host LLM router (prompts/pi/intake_router_llm.md).
route_intake is reduced to the deterministic G24 crisis floor plus a defer-to-host
default. (Crisis routing is covered in test_intake_crisis_first.py.)
"""
from __future__ import annotations

from pathlib import Path

from opl_cancer.plan.intake_router import IntakeRoute, route_intake

# The session-c3195b66 AutoML / prognosis question. Its SAFETY (decline naive
# AutoML on N=1, route to unknown_task_intake) now lives in the host LLM router +
# unknown_task_intake.md prompts, not Python keyword matching.
C3195B66_QUESTION = (
    "你会自动下载相关的公共数据库，并进行机器学习建模，"
    "找到最优的模型和参数，然后预测我的预后么"
)


def test_non_crisis_defers_to_host_llm_router() -> None:
    """A non-crisis question is no longer keyword-routed in Python; route_intake
    defers task/method composition to the host LLM router."""
    route = route_intake(C3195B66_QUESTION, profile={})
    assert isinstance(route, IntakeRoute)
    assert route.matched_task_package == "host_llm_router"
    assert route.crisis_block is False
    assert route.acknowledgement


def test_empty_question_does_not_crash() -> None:
    route = route_intake("", profile={})
    assert route.matched_task_package == "host_llm_router"
    assert route.crisis_block is False


def test_intake_route_dataclass_serialization() -> None:
    payload = route_intake(C3195B66_QUESTION, profile={}).to_dict()
    assert payload["matched_task_package"] == "host_llm_router"
    assert isinstance(payload["method_dag"], list)
    assert "crisis_block" in payload


def test_unknown_task_intake_md_file_shipped() -> None:
    """The unknown_task_intake.md prompt still ships (the host LLM router routes
    open-set questions to it for the acknowledge / decline / method-DAG / L4 flow)."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    path = repo_root / "prompts" / "tasks" / "unknown_task_intake.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for token in ("Acknowledge", "Decline", "method DAG", "L4"):
        assert token in text or token.lower() in text.lower()


def test_host_llm_router_prompt_carries_automl_safety() -> None:
    """The c3195b66 safety (naive AutoML on N=1 must be declined, not run) moved
    from Python keyword routing to the host LLM router prompt — guard that it is
    still carried there so the de-script didn't silently drop the safety."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    path = repo_root / "prompts" / "pi" / "intake_router_llm.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8").lower()
    assert "automl" in text
    assert "unknown_task_intake" in text
