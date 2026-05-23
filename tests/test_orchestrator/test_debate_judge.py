"""P2-T6: DebateJudge — LLM-driven pairwise comparison."""
from __future__ import annotations

from typing import Any

from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.debate import DebateJudge


class _FakeClient:
    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content=self.content, model=request.model)


async def test_judge_returns_winner_A() -> None:
    client = _FakeClient(content='{"winner": "A", "reason": "A mechanism is cleaner."}')
    judge = DebateJudge(client, reviewer_model_id="minimax-m2-7")
    a = Hypothesis(id="hyp_a", text="A text", rationale="A rationale")
    b = Hypothesis(id="hyp_b", text="B text", rationale="B rationale")
    out = await judge.judge_pair(a, b, context={"patient_code": "P1"})
    assert out["winner"] == "A"
    assert "mechanism" in out["reason"]


async def test_judge_handles_draw() -> None:
    client = _FakeClient(content='{"winner": "draw", "reason": "equally weak"}')
    judge = DebateJudge(client, reviewer_model_id="minimax-m2-7")
    a = Hypothesis(id="hyp_a", text="A")
    b = Hypothesis(id="hyp_b", text="B")
    out = await judge.judge_pair(a, b)
    assert out["winner"] == "draw"


async def test_judge_invalid_winner_defaults_to_draw() -> None:
    client = _FakeClient(content='{"winner": "C", "reason": "nonsense"}')
    judge = DebateJudge(client, reviewer_model_id="minimax-m2-7")
    a = Hypothesis(id="a", text="A")
    b = Hypothesis(id="b", text="B")
    out = await judge.judge_pair(a, b)
    assert out["winner"] == "draw"


async def test_judge_non_json_defaults_to_draw() -> None:
    client = _FakeClient(content="not json at all")
    judge = DebateJudge(client, reviewer_model_id="minimax-m2-7")
    a = Hypothesis(id="a", text="A")
    b = Hypothesis(id="b", text="B")
    out = await judge.judge_pair(a, b)
    assert out["winner"] == "draw"


async def test_judge_uses_reviewer_model() -> None:
    client = _FakeClient(content='{"winner": "B", "reason": "stronger"}')
    judge = DebateJudge(client, reviewer_model_id="minimax-m2-7")
    a = Hypothesis(id="a", text="A")
    b = Hypothesis(id="b", text="B")
    await judge.judge_pair(a, b)
    assert client.last_request is not None
    assert client.last_request.model == "minimax-m2-7"
