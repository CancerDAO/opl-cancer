"""P2-T11: tournament_loop.run_tournament — multi-round Elo + meta-critique."""
from __future__ import annotations

from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.tournament_loop import run_tournament


class _SeqClient:
    """Fake client that cycles through pre-canned JSON responses."""

    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


def _make_components(judge_seq: list[str], meta_seq: list[str]) -> tuple[DebateJudge, MetaCritiqueAggregator]:
    judge = DebateJudge(_SeqClient(judge_seq), reviewer_model_id="minimax-m2-7")
    agg = MetaCritiqueAggregator(_SeqClient(meta_seq), reviewer_model_id="minimax-m2-7")
    return judge, agg


async def test_single_round_n2() -> None:
    judge, agg = _make_components(
        judge_seq=['{"winner": "A", "reason": "stronger"}'],
        meta_seq=['{"meta_critique": "Round1 surface novel mech"}'],
    )
    hyps = [Hypothesis(id="h1", text="alpha"), Hypothesis(id="h2", text="beta")]
    out = await run_tournament(hyps, judge, agg, max_rounds=1)
    assert len(out["rounds"]) == 1
    assert out["final_ratings"]["h1"] > 1200.0
    assert out["final_ratings"]["h2"] < 1200.0
    assert "novel mech" in out["meta_critique_chain"][0]


async def test_multi_round_propagates_meta_critique() -> None:
    judge, agg = _make_components(
        judge_seq=['{"winner": "A", "reason": "r"}'] * 10,
        meta_seq=[
            '{"meta_critique": "Round1 critique"}',
            '{"meta_critique": "Round2 critique"}',
        ],
    )
    hyps = [Hypothesis(id="h1", text="alpha"), Hypothesis(id="h2", text="beta")]
    out = await run_tournament(
        hyps, judge, agg, max_rounds=2, convergence_window=99, convergence_threshold=0.001
    )
    assert len(out["rounds"]) == 2
    # Both critiques inherited into hypotheses
    assert any("Round1" in c for c in hyps[0].meta_critique_inherited)
    assert any("Round2" in c for c in hyps[0].meta_critique_inherited)


async def test_returns_top_k_sorted() -> None:
    judge, agg = _make_components(
        judge_seq=['{"winner": "A", "reason": ""}'] * 10,
        meta_seq=['{"meta_critique": ""}'] * 10,
    )
    hyps = [
        Hypothesis(id="h1", text="a"),
        Hypothesis(id="h2", text="b"),
        Hypothesis(id="h3", text="c"),
    ]
    out = await run_tournament(hyps, judge, agg, max_rounds=1)
    assert out["top_k"][0][0] == "h1"  # always A wins → h1 leads


async def test_skips_when_fewer_than_2() -> None:
    judge, agg = _make_components([], [])
    out = await run_tournament([Hypothesis(id="x", text="t")], judge, agg)
    assert out["rounds"] == []
    assert out["top_k"] == [("x", 1200.0)]


async def test_emits_experimental_insights_chain() -> None:
    judge, agg = _make_components(
        judge_seq=['{"winner": "A", "reason": "stronger"}'],
        meta_seq=['{"meta_critique": ""}'],
    )
    hyps = [Hypothesis(id="h1", text="alpha"), Hypothesis(id="h2", text="beta")]
    out = await run_tournament(hyps, judge, agg, max_rounds=1)
    assert len(out["experimental_insights_chain"]) == 1
    assert "Top hypotheses" in out["experimental_insights_chain"][0]
