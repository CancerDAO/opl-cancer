"""P4-T1: PISession.classify_intent_llm — LLM-backed intent classification.

Replaces P0 keyword stub (memory:feedback_default_prompt_over_script).
Tests use FakeLLMClient — no real network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer._llm_contract import LLMClient, LLMRequest, LLMResponse
from opl_cancer._llm_contract import LLMResponseParseError
from opl_cancer.orchestrator.pi_session import IntentClass, PISession


class _FakeClient(LLMClient):
    provider = "fake"

    def __init__(self, content: str) -> None:
        self._content = content

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=self._content,
            model=request.model,
            input_tokens=10,
            output_tokens=10,
        )


@pytest.mark.asyncio
async def test_classify_intent_llm_returns_new_goal(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient(json.dumps({"intent": "new_goal", "rationale": "fresh"}))
    intent = await s.classify_intent_llm(
        "请帮我分析最新的 NGS 报告",
        llm_client=client,
        model_id="minimax-m2-7",
    )
    assert intent == IntentClass.NEW_GOAL


@pytest.mark.asyncio
async def test_classify_intent_llm_returns_hypothesis_request(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient(
        json.dumps({"intent": "hypothesis_request", "rationale": "novel direction"})
    )
    intent = await s.classify_intent_llm(
        "有没有什么别的医生都没想到的方向?",
        llm_client=client,
        model_id="minimax-m2-7",
    )
    assert intent == IntentClass.HYPOTHESIS_REQUEST


@pytest.mark.asyncio
async def test_classify_intent_llm_returns_emotion(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient(
        json.dumps({"intent": "emotion", "rationale": "distress"})
    )
    intent = await s.classify_intent_llm(
        "我很害怕,睡不着",
        llm_client=client,
        model_id="minimax-m2-7",
    )
    assert intent == IntentClass.EMOTION


@pytest.mark.asyncio
async def test_classify_intent_llm_raises_on_bad_json(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient("not json at all")
    with pytest.raises(LLMResponseParseError):
        await s.classify_intent_llm(
            "hi", llm_client=client, model_id="minimax-m2-7"
        )


@pytest.mark.asyncio
async def test_classify_intent_llm_raises_on_unknown_intent(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient(
        json.dumps({"intent": "made_up_intent", "rationale": "..."})
    )
    with pytest.raises(LLMResponseParseError):
        await s.classify_intent_llm(
            "hi", llm_client=client, model_id="minimax-m2-7"
        )


@pytest.mark.asyncio
async def test_classify_intent_llm_raises_on_missing_intent_key(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    client: LLMClient = _FakeClient(json.dumps({"rationale": "no intent key"}))
    with pytest.raises(LLMResponseParseError):
        await s.classify_intent_llm(
            "hi", llm_client=client, model_id="minimax-m2-7"
        )


def test_hypothesis_request_in_intent_class() -> None:
    """P4 extension — HYPOTHESIS_REQUEST routes to Wave 2 tournament (per intent_parser.md)."""
    assert IntentClass.HYPOTHESIS_REQUEST.value == "hypothesis_request"
    assert IntentClass("hypothesis_request") == IntentClass.HYPOTHESIS_REQUEST


def test_stub_still_works_for_ci_fallback(tmp_path: Path) -> None:
    """classify_intent_stub retained for offline CI / smoke."""
    s = PISession(patient_code="p", session_dir=tmp_path)
    assert s.classify_intent_stub("我想知道有什么新方向") == IntentClass.HYPOTHESIS_REQUEST
    assert s.classify_intent_stub("hi") == IntentClass.SMALL_TALK
    assert s.classify_intent_stub("我很害怕") == IntentClass.EMOTION
