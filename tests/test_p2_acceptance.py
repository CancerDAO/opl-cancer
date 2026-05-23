"""P2-T21: Acceptance tests for v0.2.0-p2 tag.

Checks that all P2 deliverables are reachable + functional:
- Hypothesis + TournamentRound schemas
- IainExpert + AvivExpert in roster
- EloTournament machinery (pair_rotation, top_k, convergence)
- Full tournament_loop end-to-end with mocked clients
- Wave2Runner end-to-end import path
- All P2 prompt files present
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.experts.aviv import AvivExpert
from opl_cancer.experts.iain import IainExpert
from opl_cancer.experts.roster import ROSTER
from opl_cancer.glue.wave2_runner import Wave2Runner
from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import (
    Hypothesis,
    TournamentRound,
)
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.evolution import STRATEGIES as EVOL_STRATEGIES
from opl_cancer.orchestrator.evolution import EvolutionStrategist
from opl_cancer.orchestrator.generation import STRATEGIES as GEN_STRATEGIES
from opl_cancer.orchestrator.generation import HypothesisGenerator
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.reflection import MODES as REFL_MODES
from opl_cancer.orchestrator.reflection import Reflector
from opl_cancer.orchestrator.tournament import EloTournament
from opl_cancer.orchestrator.tournament_loop import run_tournament


def test_hypothesis_schema_importable() -> None:
    h = Hypothesis(id="x", text="t")
    assert h.elo_rating == 1200.0


def test_tournament_round_schema_importable() -> None:
    r = TournamentRound(round_id="r", wave_index=2)
    assert r.wave_index == 2


def test_iain_in_roster() -> None:
    assert "iain" in ROSTER
    assert ROSTER["iain"].role == "Meta-Analyst"


def test_aviv_in_roster() -> None:
    assert "aviv" in ROSTER
    assert ROSTER["aviv"].role == "Bioinformatician"


def test_iain_expert_loadable() -> None:
    assert IainExpert.portfolio == ("meta_analysis", "cross_source_consistency")


def test_aviv_expert_loadable() -> None:
    assert "hypothesis_generation" in AvivExpert.portfolio


def test_elo_pair_rotation_count() -> None:
    t = EloTournament()
    assert len(t.pair_rotation(["a", "b", "c", "d"])) == 6


def test_elo_apply_round_updates_ratings() -> None:
    t = EloTournament()
    ratings = {"a": 1200.0, "b": 1200.0}
    outcomes = [{"a": "a", "b": "b", "winner": "A"}]
    new_ratings, deltas = t.apply_round(ratings, outcomes)
    assert new_ratings["a"] > new_ratings["b"]


def test_generation_strategy_set_complete() -> None:
    assert set(GEN_STRATEGIES) == {
        "literature_gap", "cross_domain", "novel_mechanism", "feasibility_first"
    }


def test_evolution_strategy_set_complete() -> None:
    assert set(EVOL_STRATEGIES) == {
        "combination", "simplification", "extension", "analogy", "resilience", "outside_box"
    }


def test_reflection_modes_complete() -> None:
    assert set(REFL_MODES) == {
        "basic", "simulation", "observation", "deep_verification", "full_review", "falsification"
    }


def test_p2_prompts_present() -> None:
    repo = Path(__file__).resolve().parent.parent
    prompts = repo / "prompts"
    assert (prompts / "experts" / "iain" / "persona.md").exists()
    assert (prompts / "experts" / "aviv" / "persona.md").exists()
    assert (prompts / "tasks" / "meta_analysis.md").exists()
    assert (prompts / "tasks" / "hypothesis_generation.md").exists()


class _SeqClient:
    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


@pytest.mark.asyncio
async def test_full_tournament_loop_with_mocked_clients() -> None:
    judge = DebateJudge(
        _SeqClient(['{"winner":"A","reason":"r"}'] * 10),
        reviewer_model_id="minimax-m2-7",
    )
    agg = MetaCritiqueAggregator(
        _SeqClient(['{"meta_critique":"c"}'] * 10),
        reviewer_model_id="minimax-m2-7",
    )
    hyps = [
        Hypothesis(id="h1", text="alpha"),
        Hypothesis(id="h2", text="beta"),
        Hypothesis(id="h3", text="gamma"),
    ]
    out = await run_tournament(hyps, judge, agg, max_rounds=1)
    assert len(out["rounds"]) == 1
    assert len(out["top_k"]) == 3


def test_wave2_runner_importable() -> None:
    # Just exercising the import contract
    assert Wave2Runner is not None
    assert HypothesisGenerator is not None
    assert EvolutionStrategist is not None
    assert Reflector is not None
