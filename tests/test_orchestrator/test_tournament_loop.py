"""P2-T11: tournament_loop.run_tournament — multi-round Elo + meta-critique."""
from __future__ import annotations

from opl_cancer._llm_contract import LLMRequest, LLMResponse
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


class _CapturingClient:
    """Captures every request body so we can assert prompt content per round."""

    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


async def test_insights_injected_into_next_round_judge_prompt() -> None:
    """P1-7: Robin lit-loop — round-N experimental_insights must reach round-N+1 judge prompt.

    Previously written to insights_chain but never read; only meta_critique
    crossed the round boundary. This test asserts the wire is live.
    """
    judge_client = _CapturingClient(['{"winner": "A", "reason": "r"}'] * 10)
    judge = DebateJudge(judge_client, reviewer_model_id="minimax-m2-7")
    agg = MetaCritiqueAggregator(_SeqClient(['{"meta_critique": "round-meta"}'] * 10), reviewer_model_id="minimax-m2-7")
    hyps = [Hypothesis(id="h1", text="alpha"), Hypothesis(id="h2", text="beta")]
    await run_tournament(
        hyps, judge, agg, max_rounds=2, convergence_window=99, convergence_threshold=0.001
    )
    assert len(judge_client.requests) == 2  # 1 judge call per round (only one pair)
    round1_prompt = judge_client.requests[0].messages[0]["content"]
    round2_prompt = judge_client.requests[1].messages[0]["content"]

    # Round 1: no prior insights, placeholder shows (none). The label sits on
    # the same line; strip to the colon and inspect the next ~10 chars.
    assert "Experimental insights from the prior round" in round1_prompt
    after_label = round1_prompt.split("Experimental insights from the prior round", 1)[1]
    # The line is "...prior round (...explanation...): (none)\n..." — find ": " then check.
    assert ": (none)" in after_label.splitlines()[0]

    # Round 2: round-1's insights must be in the prompt — "Top hypotheses" is
    # the prose template's section header so its presence proves the wire is live.
    assert "Top hypotheses" in round2_prompt
