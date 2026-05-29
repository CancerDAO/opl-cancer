"""v2.7.1 ADR-0026 Fork B — CLI-self-sufficient Wave-1 execution, verified offline.

Proves the wiring (generic expert factory + run_wave1_live) dispatches a planned
expert and writes the provenance journal + per-expert report — using MOCK LLM
clients, no live API. Live multi-expert runs additionally need an executor key
(that is a credential/runtime concern, not a code-completeness one).
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.wave1_live import build_default_expert_factory, run_wave1_live
from opl_cancer.llm.base import LLMRequest, LLMResponse


class _LoopStub:
    """Mock LLM client: returns queued responses, then a safe default JSON.

    Forgiving on exact call-count so the test asserts the dispatch STRUCTURE
    (experts run, artifacts land) without pinning the runner's internal call
    sequence."""

    provider = "stub"

    def __init__(self, responses: list[str], default: str = '{"summary": "stub", "claims": []}') -> None:
        self.responses = list(responses)
        self.default = default

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses.pop(0) if self.responses else self.default
        return LLMResponse(content=body, model=request.model, input_tokens=1,
                           output_tokens=1, finish_reason="end_turn")


def _patient(tmp_path: Path) -> Path:
    p = tmp_path / "anon_x"
    p.mkdir()
    (p / "profile.json").write_text(json.dumps({
        "patient_code": "anon_x",
        "diagnosis": {"primary_site": "lung", "histology": "NSCLC"},
        "preferences": {"language": "en"},
    }))
    (p / "readiness.json").write_text('{"grade": "B"}')
    (p / "case_text.md").write_text("EGFR L858R-mutated NSCLC.")
    bucket = p / "02_NGS报告"
    bucket.mkdir()
    (bucket / "ngs.txt").write_text("EGFR L858R, VAF 0.45")
    return p


def test_default_factory_builds_any_roster_expert() -> None:
    """The generic factory must build a working expert for personas with NO
    concrete subclass (vince, empty portfolio) and the v2 additions (maya/julius)."""
    factory = build_default_expert_factory()
    vince = factory("vince", _LoopStub([]), _LoopStub([]), "exec-id", "rev-id")
    assert vince.profile.name == "vince"
    assert vince.can_handle("anything")  # empty portfolio → trusts planner routing
    for n in ("maya", "julius", "frances", "rosa"):
        assert factory(n, _LoopStub([]), _LoopStub([]), "e", "r").profile.name == n


def test_wave1_live_self_executes_and_writes_provenance(tmp_path: Path) -> None:
    """run_wave1_live with the GENERIC factory drives the real Wave1Runner and
    leaves the artifacts audit/deliver/attest look for — fully offline."""
    patient = _patient(tmp_path)
    run_root = tmp_path / "triggers" / "r1"
    intent = _LoopStub(['{"intent": "NEW_GOAL", "rationale": "ngs question"}'])
    planner = _LoopStub([
        '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
        '"task_package":"molecular_ngs_interpretation","sub_goal":"interpret ngs"}]}'
    ])
    executor = _LoopStub([
        '{"variants": [{"gene": "EGFR", "protein_change": "L858R", '
        '"claim_layer": "established", "evidence": [{"type":"pmid","id":"31157963",'
        '"quote":"Osimertinib improves OS"}], "summary": "actionable EGFR L858R"}], '
        '"summary": "actionable"}'
    ])
    reviewer = _LoopStub(['{"verdict": "pass", "challenges": []}'])

    result = run_wave1_live(
        patient_root=patient, run_root=run_root,
        intent_client=intent, planner_client=planner,
        executor_client=executor, reviewer_client=reviewer,
        executor_model_id="claude-opus-4-7", reviewer_model_id="minimax-m2-7",
        expert_factory=build_default_expert_factory(),
    )
    assert result["status"] == "ok", result
    # the dispatch left the artifacts the downstream gates read:
    assert (run_root / "provenance.jsonl").exists(), "provenance journal must be written"
    reports = list(run_root.glob("tasks/w1_*/report.md"))
    assert reports, "at least one per-expert report must be written"
    assert any("bert" in r.read_text(encoding="utf-8") for r in reports)
