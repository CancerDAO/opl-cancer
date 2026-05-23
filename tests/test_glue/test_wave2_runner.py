"""P2-T16: Wave2Runner end-to-end (hypothesis generation + tournament + reflection)."""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.wave2_runner import Wave2Runner
from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.evolution import EvolutionStrategist
from opl_cancer.orchestrator.generation import HypothesisGenerator
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.reflection import Reflector


class _SeqClient:
    """Cycles through canned responses keyed by call index."""

    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


_GEN_JSON = (
    '{"text":"H novel direction","rationale":"r","evidence_refs":[{"type":"pmid","id":"123"}]}'
)
_EVOLVE_JSON = '{"text":"H evolved","rationale":"r2","evidence_refs":[]}'
_JUDGE_JSON = '{"winner":"A","reason":"stronger"}'
_META_JSON = '{"meta_critique":"Round critique"}'
_REFLECT_JSON = '{"verdict":"passes","rationale":"clean"}'


def _make_runner(tmp_path: Path) -> Wave2Runner:
    # Each component gets its own seq client (they consume from different streams)
    gen_client = _SeqClient([_GEN_JSON] * 4)
    evo_client = _SeqClient([_EVOLVE_JSON] * 2)
    judge_client = _SeqClient([_JUDGE_JSON] * 50)
    meta_client = _SeqClient([_META_JSON] * 10)
    refl_client = _SeqClient([_REFLECT_JSON] * 10)

    return Wave2Runner(
        out_dir=tmp_path / "out",
        hypothesis_generator=HypothesisGenerator(gen_client, executor_model_id="claude-opus-4-7"),
        evolution_strategist=EvolutionStrategist(evo_client, executor_model_id="claude-opus-4-7"),
        reflector=Reflector(refl_client, reviewer_model_id="minimax-m2-7"),
        judge=DebateJudge(judge_client, reviewer_model_id="minimax-m2-7"),
        aggregator=MetaCritiqueAggregator(meta_client, reviewer_model_id="minimax-m2-7"),
        max_tournament_rounds=1,
    )


async def test_wave2_runner_produces_hypotheses(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("What novel directions exist?", patient_context={"cancer": "HCC"})
    # 4 from generation + 2 from evolution = 6
    assert len(out["hypotheses"]) == 6
    assert len(out["top_k"]) <= 5


async def test_wave2_runner_writes_json(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    run_dir = tmp_path / "out" / out["run_id"]
    assert (run_dir / "wave2_hypotheses.json").exists()
    payload = json.loads((run_dir / "wave2_hypotheses.json").read_text())
    assert "hypotheses" in payload
    assert "rounds" in payload
    assert "reflections" in payload


async def test_wave2_runner_provenance_written(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    prov = tmp_path / "out" / out["run_id"] / "provenance.jsonl"
    assert prov.exists()
    lines = prov.read_text().strip().splitlines()
    assert len(lines) >= 6  # one per hypothesis


async def test_wave2_runner_reflections_per_top_hypothesis(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    assert len(out["reflections"]) <= 3
    for r in out["reflections"]:
        assert "basic" in r
        assert "falsification" in r
