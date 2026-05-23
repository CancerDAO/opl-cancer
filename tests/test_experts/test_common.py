"""Test LLMBackedExpert — shared 6-primitive grammar wrapper.

Plan refs: P1-T25.
LLM calls mocked via injected fake client so tests stay offline + deterministic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.base import ExpertProfile
from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.llm.errors import LLMResponseParseError


class _FakeClient:
    """Minimal LLMClient stand-in — records last request + returns canned content."""

    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_request: LLMRequest | None = None
        self.call_count = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        self.call_count += 1
        return LLMResponse(
            content=self.content,
            model=request.model,
            input_tokens=10,
            output_tokens=5,
            finish_reason="end_turn",
        )


class _StubIntegrator:
    family = "F1"

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[str] = []

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        self.calls.append(key)
        return self._payload


class _DummyExpert(LLMBackedExpert):
    """Concrete subclass for testing — minimal portfolio."""

    portfolio = ("dummy_task",)
    preferred_families = ("F1",)


@pytest.fixture()
def dummy_task_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Create a dummy_task.md under a tmp prompts root + dummy persona file."""
    prompts_root = tmp_path / "prompts"
    (prompts_root / "tasks").mkdir(parents=True)
    (prompts_root / "experts" / "dummy").mkdir(parents=True)
    (prompts_root / "tasks" / "dummy_task.md").write_text(
        "Task body with {{ key }}.", encoding="utf-8"
    )
    (prompts_root / "experts" / "dummy" / "persona.md").write_text(
        "You are dummy.", encoding="utf-8"
    )

    def _fake_root() -> Path:
        return prompts_root

    monkeypatch.setattr("opl_cancer.experts._common.find_prompts_root", _fake_root)
    return prompts_root


def _profile(name: str = "dummy") -> ExpertProfile:
    return ExpertProfile(
        name=name,
        role="Dummy",
        inspiration="N/A",
        persona_summary="...",
        task_package_portfolio=["dummy_task"],
        preferred_integrator_families=["F1"],
    )


def test_can_handle_filters_portfolio() -> None:
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    assert exp.can_handle("dummy_task")
    assert not exp.can_handle("some_other_task")


async def test_plan_returns_portfolio_decomposition() -> None:
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    plan = await exp.plan("sub-goal X", context={})
    assert plan["expert"] == "dummy"
    assert plan["sub_goal"] == "sub-goal X"
    assert plan["task_packages"] == ["dummy_task"]


async def test_execute_parses_json_response(dummy_task_prompt: Path) -> None:
    fake = _FakeClient(content='{"variants": [], "summary": "ok"}')
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=fake,
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    result = await exp.execute("dummy_task", plan={}, context={"key": "val"})
    assert result["variants"] == []
    assert result["summary"] == "ok"
    # meta annotates with executor model + prompt version
    meta = result["_meta"]
    assert meta["model"] == "claude-opus-4-7"
    assert meta["executor_task"] == "dummy_task"
    assert "dummy_task" in meta["prompt_version"]
    assert meta["input_tokens"] == 10
    assert meta["output_tokens"] == 5


async def test_execute_uses_persona_as_system_prompt(dummy_task_prompt: Path) -> None:
    fake = _FakeClient(content="{}")
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=fake,
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    await exp.execute("dummy_task", plan={}, context={"key": "val"})
    assert fake.last_request is not None
    assert fake.last_request.system == "You are dummy."
    # prompt was rendered with context vars
    assert "Task body with val" in fake.last_request.messages[0]["content"]


async def test_execute_raises_on_bad_json(dummy_task_prompt: Path) -> None:
    fake = _FakeClient(content="not json at all")
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=fake,
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    with pytest.raises(LLMResponseParseError):
        await exp.execute("dummy_task", plan={}, context={"key": "val"})


async def test_execute_raises_on_unknown_task(dummy_task_prompt: Path) -> None:
    fake = _FakeClient(content="{}")
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=fake,
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    with pytest.raises(ValueError):
        await exp.execute("not_in_portfolio", plan={}, context={})


async def test_review_returns_verdict() -> None:
    reviewer = _FakeClient(
        content='{"verdict": "pass", "challenges": []}'
    )
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=reviewer,
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    verdict = await exp.review({"variants": []}, context={})
    assert verdict["verdict"] == "pass"
    assert verdict["reviewer_model"] == "minimax-m2-7"
    # reviewer was called with reviewer's model id, not executor's
    assert reviewer.last_request is not None
    assert reviewer.last_request.model == "minimax-m2-7"


async def test_review_handles_non_json_response() -> None:
    reviewer = _FakeClient(content="this is not JSON")
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=reviewer,
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    verdict = await exp.review({"variants": []}, context={})
    # graceful: marked needs_revision rather than crashing
    assert verdict["verdict"] == "needs_revision"
    assert verdict["challenges"]
    assert verdict["reviewer_model"] == "minimax-m2-7"


async def test_audit_returns_intra_expert_marker() -> None:
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    result = await exp.audit({"claim": "x"})
    assert result["intra_expert_audit"] == "ok"
    assert result["expert"] == "dummy"


async def test_integrate_uses_injected_integrator() -> None:
    integ = _StubIntegrator(payload={"pmid": "12345", "title": "Test"})
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        integrators={"F1": integ},
    )
    result = await exp.integrate("F1", "PMID:12345")
    assert result["pmid"] == "12345"
    assert integ.calls == ["PMID:12345"]


async def test_integrate_raises_for_missing_family() -> None:
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    with pytest.raises(KeyError):
        await exp.integrate("F1", "PMID:1")


def test_feedback_is_a_noop_in_p1() -> None:
    exp = _DummyExpert(
        profile=_profile(),
        executor_client=_FakeClient(content="{}"),
        reviewer_client=_FakeClient(content="{}"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    # MUST NOT raise. Working memory update lives in P2.
    assert exp.feedback({"event": "trial_started"}) is None
