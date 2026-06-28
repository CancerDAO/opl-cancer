"""P2-T10: Reflector — 6 modes."""
from __future__ import annotations

import pytest

from opl_cancer._llm_contract import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.reflection import MODES, Reflector


class _FakeClient:
    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=self.content, model=request.model)


_PASSES = '{"verdict":"passes","rationale":"clean mechanism"}'
_FALSIFIED = '{"verdict":"falsified","rationale":"core premise wrong"}'


async def test_reflect_basic_passes() -> None:
    h = Hypothesis(id="x", text="t", rationale="r")
    r = Reflector(_FakeClient(_PASSES), reviewer_model_id="minimax-m2-7")
    out = await r.reflect("basic", h)
    assert out["verdict"] == "passes"
    assert out["mode"] == "basic"


async def test_reflect_falsification_falsified() -> None:
    h = Hypothesis(id="x", text="t")
    r = Reflector(_FakeClient(_FALSIFIED), reviewer_model_id="minimax-m2-7")
    out = await r.reflect("falsification", h)
    assert out["verdict"] == "falsified"


async def test_reflect_all_modes() -> None:
    h = Hypothesis(id="x", text="t")
    r = Reflector(_FakeClient(_PASSES), reviewer_model_id="minimax-m2-7")
    for m in MODES:
        out = await r.reflect(m, h)
        assert out["mode"] == m


async def test_reflect_unknown_mode() -> None:
    h = Hypothesis(id="x", text="t")
    r = Reflector(_FakeClient(_PASSES), reviewer_model_id="minimax-m2-7")
    with pytest.raises(ValueError):
        await r.reflect("invalid_mode", h)


async def test_reflect_non_json_returns_weakened() -> None:
    h = Hypothesis(id="x", text="t")
    r = Reflector(_FakeClient("garbage"), reviewer_model_id="minimax-m2-7")
    out = await r.reflect("basic", h)
    assert out["verdict"] == "weakened"


async def test_reflect_invalid_verdict_defaults_weakened() -> None:
    h = Hypothesis(id="x", text="t")
    r = Reflector(
        _FakeClient('{"verdict":"unknown","rationale":""}'),
        reviewer_model_id="minimax-m2-7",
    )
    out = await r.reflect("basic", h)
    assert out["verdict"] == "weakened"


async def test_reflect_truncates_long_rationale() -> None:
    h = Hypothesis(id="x", text="t")
    long = "y" * 5000
    r = Reflector(
        _FakeClient(f'{{"verdict":"passes","rationale":"{long}"}}'),
        reviewer_model_id="minimax-m2-7",
    )
    out = await r.reflect("basic", h)
    assert len(out["rationale"]) <= 1000
