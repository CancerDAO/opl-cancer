"""Test LLMBackedExpert — shared 6-primitive grammar scaffold/validator.

Plan refs: P1-T25, harness-split (HARNESS_SPLIT_PRD).
Harness-split: the expert no longer calls an LLM. ``execute`` returns the
host-written report artifact (loaded + validated) when present, else a scaffold
placeholder; ``review`` defers to a host-agent reviewer subagent. These tests
assert that deterministic scaffold/validate behavior — no LLM client involved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from opl_cancer.experts._common import ExpertArtifactError, LLMBackedExpert
from opl_cancer.experts.base import ExpertProfile


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
    """Create a dummy_task.md under a tmp prompts root + dummy persona file.

    v1.5.2-2: also writes a minimal _shared/persona_prefix.md so the
    auto-prepend introduced in this iteration can find it. Real persona
    runs always have the full v1.5 P1-A prefix; this stub satisfies the
    loader.
    """
    prompts_root = tmp_path / "prompts"
    (prompts_root / "tasks").mkdir(parents=True)
    (prompts_root / "experts" / "dummy").mkdir(parents=True)
    (prompts_root / "experts" / "_shared").mkdir(parents=True)
    (prompts_root / "tasks" / "dummy_task.md").write_text(
        "Task body with {{ key }}.", encoding="utf-8"
    )
    (prompts_root / "experts" / "dummy" / "persona.md").write_text(
        "You are dummy.", encoding="utf-8"
    )
    (prompts_root / "experts" / "_shared" / "persona_prefix.md").write_text(
        "# G7 voice + Patient-anchor + Source-traceability\nTest stub.",
        encoding="utf-8",
    )

    def _fake_root() -> Path:
        return prompts_root

    monkeypatch.setattr("opl_cancer.experts._common.find_prompts_root", _fake_root)
    # v1.5.2-2: reset class-level cache so the tmp_path is picked up
    LLMBackedExpert._persona_prefix_cache = None
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


def _expert(name: str = "dummy", **kwargs: Any) -> "_DummyExpert":
    """Build a _DummyExpert with the harness-split signature (no LLM clients)."""
    return _DummyExpert(
        profile=_profile(name),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        **kwargs,
    )


def test_can_handle_filters_portfolio() -> None:
    exp = _expert()
    assert exp.can_handle("dummy_task")
    assert not exp.can_handle("some_other_task")


async def test_plan_returns_portfolio_decomposition() -> None:
    exp = _expert()
    plan = await exp.plan("sub-goal X", context={})
    assert plan["expert"] == "dummy"
    assert plan["sub_goal"] == "sub-goal X"
    assert plan["task_packages"] == ["dummy_task"]


async def test_scaffold_composes_persona_and_task(dummy_task_prompt: Path) -> None:
    exp = _expert()
    scaffold = exp.scaffold("dummy_task", context={"key": "val"}, sub_goal="sg")
    # system prompt = canonical prefix + persona body
    assert "You are dummy." in scaffold["system_prompt"]
    assert "G7 voice" in scaffold["system_prompt"]
    # task instructions rendered with context vars
    assert "Task body with val" in scaffold["task_instructions"]
    # points at the host-agent execute prompt + carries provenance labels
    assert scaffold["execute_prompt"].endswith("expert_task_package.md")
    assert "dummy_task" in scaffold["prompt_version"]
    assert scaffold["response_format"] == "json_object"


async def test_execute_returns_host_artifact_when_present(dummy_task_prompt: Path) -> None:
    """When the host agent has written the report, execute loads + validates it."""
    exp = _expert()
    host = {"variants": [], "summary": "ok"}
    result = await exp.execute(
        "dummy_task", plan={},
        context={"key": "val", "_host_artifacts": {"dummy_task": host}},
    )
    assert result["variants"] == []
    assert result["summary"] == "ok"
    # _meta provenance stamped by validate_artifact
    meta = result["_meta"]
    assert meta["model"] == "claude-opus-4-7"
    assert meta["executor_task"] == "dummy_task"
    assert meta["produced_by"] == "host-agent"


async def test_execute_loads_host_artifact_from_disk(dummy_task_prompt: Path, tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "dummy_dummy_task.json").write_text(
        '{"matches": [], "summary": "from-disk"}', encoding="utf-8"
    )
    exp = _expert()
    result = await exp.execute(
        "dummy_task", plan={}, context={"_artifact_dir": str(artifact_dir)}
    )
    assert result["summary"] == "from-disk"
    assert result["_meta"]["produced_by"] == "host-agent"


async def test_execute_returns_scaffold_placeholder_when_no_artifact(dummy_task_prompt: Path) -> None:
    """No host artifact yet → scaffold placeholder (produced_by='scaffold'),
    never a fabricated/approving result."""
    exp = _expert()
    result = await exp.execute("dummy_task", plan={"sub_goal": "sg"}, context={"key": "val"})
    assert result["produced_by"] == "scaffold"
    assert result["_meta"]["produced_by"] == "scaffold"
    # carries the scaffold the host agent must run
    assert "You are dummy." in result["_scaffold"]["system_prompt"]
    # no claim lists → contributes zero claims downstream (honest emptiness)
    assert "variants" not in result


async def test_validate_artifact_raises_on_non_dict() -> None:
    exp = _expert()
    with pytest.raises(ExpertArtifactError):
        exp.validate_artifact("dummy_task", ["not", "a", "dict"])  # type: ignore[arg-type]


async def test_execute_raises_on_bad_disk_json(dummy_task_prompt: Path, tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "dummy_dummy_task.json").write_text("not json at all", encoding="utf-8")
    exp = _expert()
    with pytest.raises(ExpertArtifactError):
        await exp.execute("dummy_task", plan={}, context={"_artifact_dir": str(artifact_dir)})


async def test_execute_raises_on_unknown_task(dummy_task_prompt: Path) -> None:
    exp = _expert()
    with pytest.raises(ValueError):
        await exp.execute("not_in_portfolio", plan={}, context={})


async def test_review_defers_to_host_reviewer() -> None:
    """Harness-split: review no longer makes a cross-model LLM call. It returns a
    deterministic 'deferred' verdict (the real reviewer is a host subagent)."""
    exp = _expert()
    verdict = await exp.review({"variants": []}, context={})
    assert verdict["verdict"] == "deferred_to_host_reviewer"
    assert verdict["reviewer_model"] == "minimax-m2-7"
    assert verdict["challenges"] == []


async def test_audit_returns_intra_expert_marker() -> None:
    exp = _expert()
    result = await exp.audit({"claim": "x"})
    assert result["intra_expert_audit"] == "ok"
    assert result["expert"] == "dummy"


async def test_integrate_uses_injected_integrator() -> None:
    integ = _StubIntegrator(payload={"pmid": "12345", "title": "Test"})
    exp = _expert(integrators={"F1": integ})
    result = await exp.integrate("F1", "PMID:12345")
    assert result["pmid"] == "12345"
    assert integ.calls == ["PMID:12345"]


async def test_integrate_raises_for_missing_family() -> None:
    exp = _expert()
    with pytest.raises(KeyError):
        await exp.integrate("F1", "PMID:1")


def test_feedback_is_a_noop_in_p1() -> None:
    exp = _expert()
    import warnings as _w

    with _w.catch_warnings():
        _w.simplefilter("always")
        assert exp.feedback({"event": "trial_started"}) is None


async def test_stub_methods_emit_warnings() -> None:
    """P1-5: plan/audit/feedback are stubs — they must warn so callers know."""
    import warnings as _w

    from opl_cancer.experts._common import StubMethodWarning

    exp = _expert()

    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        await exp.plan("sub-goal", context={})
        await exp.audit({"claim": "x"})
        exp.feedback({"event": "x"})

    stub_warnings = [w for w in caught if issubclass(w.category, StubMethodWarning)]
    assert len(stub_warnings) == 3, (
        f"expected 3 StubMethodWarnings (plan/audit/feedback), got {len(stub_warnings)}: "
        f"{[(w.category.__name__, str(w.message)) for w in caught]}"
    )
    msgs = [str(w.message) for w in stub_warnings]
    assert any("plan()" in m for m in msgs)
    assert any("audit()" in m for m in msgs)
    assert any("feedback()" in m for m in msgs)
