"""P2-T19: End-to-end hypothesis flow on synthetic patient.

Runs Wave2Runner with all LLM clients mocked. Asserts:
- ≥3 ranked hypotheses produced
- provenance.jsonl written
- wave2_hypotheses.json valid
- founder-mode: all hypotheses default to speculative layer
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.wave2_runner import Wave2Runner
from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import ClaimLayer
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.evolution import EvolutionStrategist
from opl_cancer.orchestrator.generation import HypothesisGenerator
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.reflection import Reflector


class _SeqClient:
    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


_GEN = (
    '{"text":"WNT/β-catenin inhibitor + ICI combination in HBV+ HCC","'
    'rationale":"Mech link via β-catenin → T-cell exclusion","'
    'evidence_refs":[{"type":"pmid","id":"38219045"}]}'
)
_EVO = (
    '{"text":"Sequential anti-PD-L1 → Wnt inhibitor in TACE-refractory HCC","'
    'rationale":"avoids overlap toxicity","evidence_refs":[]}'
)
_JUDGE = '{"winner":"A","reason":"more falsifiable"}'
_META = '{"meta_critique":"Round flagged HBV confounding"}'
_REFL = '{"verdict":"passes","rationale":"mechanism consistent"}'


async def test_e2e_hcc_hypothesis_flow(tmp_path: Path) -> None:
    runner = Wave2Runner(
        out_dir=tmp_path / "out",
        hypothesis_generator=HypothesisGenerator(
            _SeqClient([_GEN] * 10), executor_model_id="claude-opus-4-7"
        ),
        evolution_strategist=EvolutionStrategist(
            _SeqClient([_EVO] * 10), executor_model_id="claude-opus-4-7"
        ),
        reflector=Reflector(
            _SeqClient([_REFL] * 10), reviewer_model_id="minimax-m2-7"
        ),
        judge=DebateJudge(
            _SeqClient([_JUDGE] * 100), reviewer_model_id="minimax-m2-7"
        ),
        aggregator=MetaCritiqueAggregator(
            _SeqClient([_META] * 10), reviewer_model_id="minimax-m2-7"
        ),
        max_tournament_rounds=2,
    )

    patient_text = "What novel research directions exist for my HBV+ HCC?"
    patient_context = {
        "patient_code": "HCC_SYN001",
        "diagnosis": {"histology": "HCC", "primary_site": "liver"},
        "molecular_profile": {"TP53": "mut", "CTNNB1": "mut"},
        "treatment_history": ["TACE x3 (progressive)"],
    }
    wave1_outputs = {
        "pubmed_summary": "WNT/β-catenin signaling links to ICI non-response (PMID:38219045)."
    }

    out = await runner.run(patient_text, patient_context, wave1_outputs)

    # ≥3 hypotheses
    assert len(out["hypotheses"]) >= 3

    # Founder-mode: hypotheses default to speculative
    for h in out["hypotheses"]:
        assert h["claim_layer"] == ClaimLayer.SPECULATIVE.value

    # Tournament produced rounds + top_k
    assert len(out["rounds"]) >= 1
    assert len(out["top_k"]) >= 3

    # Reflections cover top-3
    assert len(out["reflections"]) == 3

    # Provenance + JSON written
    run_dir = tmp_path / "out" / out["run_id"]
    assert (run_dir / "provenance.jsonl").exists()
    assert (run_dir / "wave2_hypotheses.json").exists()
    payload = json.loads((run_dir / "wave2_hypotheses.json").read_text())
    assert payload["run_id"] == out["run_id"]
