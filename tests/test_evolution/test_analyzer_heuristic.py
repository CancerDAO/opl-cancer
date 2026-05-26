"""Analyzer tests — heuristic fallback path + LLM mock + refuses unscrubbed."""
from __future__ import annotations

from typing import Any

import pytest

from opl_cancer.evolution.analyzer import EvolutionAnalyzer
from opl_cancer.evolution.models import (
    HypothesisStrategyCount,
    TraceDigest,
)


def _digest_missing_v2_strategies() -> TraceDigest:
    return TraceDigest(
        run_id="run-weak",
        patient_code_scrubbed="[SCRUBBED]",
        hypothesis_strategies=[
            HypothesisStrategyCount(strategy="literature_gap", count=2),
            HypothesisStrategyCount(strategy="feasibility_first", count=2),
        ],
        novelty_gate_stats={"world_unknown_section_present": 0},
    )


def _digest_strong() -> TraceDigest:
    return TraceDigest(
        run_id="run-strong",
        patient_code_scrubbed="[SCRUBBED]",
        hypothesis_strategies=[
            HypothesisStrategyCount(strategy="literature_gap", count=2),
            HypothesisStrategyCount(strategy="target_synergy_emergent", count=1, speculative_with_testability=1),
            HypothesisStrategyCount(strategy="undrugged_target_design", count=1, speculative_with_testability=1),
        ],
        novelty_gate_stats={"world_unknown_section_present": 1},
    )


async def test_analyzer_refuses_unscrubbed_digest():
    digest = TraceDigest(run_id="run-x", patient_code_scrubbed="PT-EE62321353")
    a = EvolutionAnalyzer()
    with pytest.raises(ValueError, match="unscrubbed digest"):
        await a.analyze(digest)


async def test_heuristic_fallback_proposes_strategy_gaps():
    digest = _digest_missing_v2_strategies()
    a = EvolutionAnalyzer()
    cands = await a.analyze(digest, iter_n=1)
    assert cands.used_heuristic_fallback is True
    summaries = [p.summary for p in cands.proposals]
    assert any("target_synergy_emergent" in s for s in summaries)
    assert any("undrugged_target_design" in s for s in summaries)


async def test_heuristic_fallback_no_proposals_on_strong_run():
    digest = _digest_strong()
    a = EvolutionAnalyzer()
    cands = await a.analyze(digest, iter_n=1)
    assert cands.used_heuristic_fallback is True
    # No structural gaps to flag
    assert len(cands.proposals) == 0


class _FakeLLMResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.input_tokens = 0
        self.output_tokens = 0


class _FakeLLM:
    """Returns canned JSON response."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    async def complete(self, request: Any) -> Any:
        return _FakeLLMResponse(self._payload)


async def test_llm_path_materialises_proposals():
    digest = _digest_missing_v2_strategies()
    fake_response = (
        '{"analysis_summary": "weak run", '
        '"proposals": ['
        '{"kind": "prompt_patch", "summary": "add synergy slot", '
        '"rationale": "no target_synergy_emergent in digest", '
        '"target_path": "prompts/experts/maya/persona.md", '
        '"proposed_diff": "--- old\\n+++ new\\n+ add synergy"}'
        ']}'
    )
    a = EvolutionAnalyzer(
        llm_client=_FakeLLM(fake_response),
        model_id="fake-test-model",
    )
    cands = await a.analyze(digest, iter_n=2)
    assert cands.used_heuristic_fallback is False
    assert cands.analyzer_model == "fake-test-model"
    assert len(cands.proposals) == 1
    assert cands.proposals[0].kind == "prompt_patch"


async def test_llm_failure_falls_back_to_heuristic():
    class _BrokenLLM:
        async def complete(self, request: Any) -> Any:
            raise RuntimeError("network down")

    digest = _digest_missing_v2_strategies()
    a = EvolutionAnalyzer(llm_client=_BrokenLLM(), model_id="broken")
    cands = await a.analyze(digest, iter_n=3)
    # Per memory:feedback_no_offline_only this fallback is allowed BECAUSE
    # it is loud (used_heuristic_fallback=True surfaced).
    assert cands.used_heuristic_fallback is True
    assert "LLM analyzer failed" in cands.analysis_summary


async def test_llm_path_invariant_gate_applied():
    """Proposal touching Henry must come back with requires_double_signoff=True."""
    digest = _digest_missing_v2_strategies()
    fake_response = (
        '{"analysis_summary": "soft Henry", '
        '"proposals": ['
        '{"kind": "prompt_patch", "summary": "soften Henry L3", '
        '"rationale": "speed up runs", '
        '"target_path": "src/opl_cancer/validators/henry.py", '
        '"proposed_diff": "disable requires_acknowledgment for L3"}'
        ']}'
    )
    a = EvolutionAnalyzer(llm_client=_FakeLLM(fake_response), model_id="fake")
    cands = await a.analyze(digest, iter_n=1)
    p = cands.proposals[0]
    assert p.requires_double_signoff is True
    assert p.invariant_impact.touches_henry_l3_l4 is True


async def test_llm_path_caps_proposals_at_5():
    digest = _digest_missing_v2_strategies()
    proposals_raw = ",".join(
        f'{{"kind": "prompt_patch", "summary": "p{i}", "rationale": "r", '
        f'"target_path": "x.md", "proposed_diff": "d"}}'
        for i in range(10)
    )
    fake_response = f'{{"analysis_summary": "many", "proposals": [{proposals_raw}]}}'
    a = EvolutionAnalyzer(llm_client=_FakeLLM(fake_response), model_id="fake")
    cands = await a.analyze(digest, iter_n=1)
    assert len(cands.proposals) <= 5
