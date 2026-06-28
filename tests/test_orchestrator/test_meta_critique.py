"""P2-T7: MetaCritiqueAggregator."""
from __future__ import annotations

from opl_cancer._llm_contract import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator


class _FakeClient:
    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content=self.content, model=request.model)


async def test_aggregate_returns_critique_string() -> None:
    client = _FakeClient(content='{"meta_critique": "Round flagged confounding by HBV status."}')
    agg = MetaCritiqueAggregator(client, reviewer_model_id="minimax-m2-7")
    outcomes = [{"a": "hyp_a", "b": "hyp_b", "winner": "A", "reason": "…"}]
    hyps = [Hypothesis(id="hyp_a", text="A"), Hypothesis(id="hyp_b", text="B")]
    out = await agg.aggregate(outcomes, hyps)
    assert "HBV" in out


async def test_aggregate_non_json_returns_empty() -> None:
    client = _FakeClient(content="garbage")
    agg = MetaCritiqueAggregator(client, reviewer_model_id="minimax-m2-7")
    out = await agg.aggregate([], [])
    assert out == ""


async def test_aggregate_truncates_long_output() -> None:
    long = "x" * 5000
    client = _FakeClient(content=f'{{"meta_critique": "{long}"}}')
    agg = MetaCritiqueAggregator(client, reviewer_model_id="minimax-m2-7")
    out = await agg.aggregate([], [])
    assert len(out) <= 2000


async def test_aggregate_uses_reviewer_model() -> None:
    client = _FakeClient(content='{"meta_critique": "ok"}')
    agg = MetaCritiqueAggregator(client, reviewer_model_id="minimax-m2-7")
    await agg.aggregate([], [])
    assert client.last_request is not None
    assert client.last_request.model == "minimax-m2-7"
