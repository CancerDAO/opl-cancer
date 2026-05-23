"""Test Wave1Runner end-to-end with mocked LLM clients.

Mocks every LLM call (intent, planner, executor, reviewer) via _Stub so the
test never touches a real API. Verifies the full pipeline produces a
patient_brief.html with three-tier labels + PMID links + provenance hash.
"""
import json
from pathlib import Path
from typing import Any

from opl_cancer.experts.bert import BertExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import Wave1Runner
from opl_cancer.llm.base import LLMRequest, LLMResponse


class _Stub:
    """Stub LLM client — returns canned responses in order."""

    provider = "stub"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.responses:
            raise RuntimeError(f"_Stub out of responses for model={request.model}")
        body = self.responses.pop(0)
        return LLMResponse(
            content=body,
            model=request.model,
            input_tokens=1,
            output_tokens=1,
            finish_reason="end_turn",
        )


class _FakeIntegrator:
    family = "F4"
    ttl_seconds = 60
    cache = None

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        self.calls.append(key)
        return {"verified": True, "key": key}


def _setup_patient(tmp_path: Path) -> Path:
    patient_root = tmp_path / "anon_001"
    patient_root.mkdir()
    (patient_root / "profile.json").write_text(json.dumps({
        "patient_code": "anon_001",
        "demographics": {"age": 56, "sex": "M"},
        "diagnosis": {"primary_site": "lung", "histology": "NSCLC"},
        "treatment_history": [],
        "preferences": {"depth": "technical", "language": "zh-CN"},
    }))
    (patient_root / "readiness.json").write_text("{}")
    (patient_root / "case_text.md").write_text("EGFR L858R-mutated NSCLC.")
    bucket = patient_root / "02_NGS报告"
    bucket.mkdir()
    (bucket / "ngs.txt").write_text("EGFR L858R, VAF 0.45")
    return patient_root


def _bert_factory(name: str, exec_c: Any, rev_c: Any, ex_id: str, rv_id: str) -> Any:
    return BertExpert(
        profile=get_expert_profile("bert"),
        executor_client=exec_c,
        reviewer_client=rev_c,
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={"F4": _FakeIntegrator(), "F5": _FakeIntegrator()},
    )


async def test_wave1_runner_produces_brief(tmp_path: Path) -> None:
    patient_root = _setup_patient(tmp_path)
    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        intent_client=_Stub(['{"intent": "NEW_GOAL", "rationale": "ngs question"}']),
        planner_client=_Stub([
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"interpret ngs"}]}'
        ]),
        executor_client=_Stub([
            '{"variants": [{"gene": "EGFR", "protein_change": "L858R", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"31157963",'
            '"quote":"Osimertinib improves OS"}], "summary": "actionable EGFR L858R"}], '
            '"summary": "actionable"}'
        ]),
        reviewer_client=_Stub(['{"verdict": "pass", "challenges": []}']),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )

    result = await runner.run(patient_text="我想了解我的 NGS 结果")
    assert result["status"] == "ok"

    brief_html = tmp_path / "out" / "delivery" / "patient_brief.html"
    assert brief_html.exists()
    text = brief_html.read_text(encoding="utf-8")
    assert "EGFR" in text


async def test_wave1_runner_three_tier_label_pmid_provenance(tmp_path: Path) -> None:
    """E2E assertion: brief contains three-tier label, PMID link, and provenance hash."""
    patient_root = _setup_patient(tmp_path)
    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        intent_client=_Stub(['{"intent": "NEW_GOAL", "rationale": "x"}']),
        planner_client=_Stub([
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"interpret ngs"}]}'
        ]),
        executor_client=_Stub([
            '{"variants": [{"gene": "EGFR", "protein_change": "L858R", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"31157963",'
            '"quote":"Osimertinib improves OS"}], "summary": "actionable EGFR L858R"}], '
            '"summary": "actionable"}'
        ]),
        reviewer_client=_Stub(['{"verdict": "pass", "challenges": []}']),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )
    await runner.run(patient_text="ngs?")
    text = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(encoding="utf-8")

    # Three-tier label badge
    assert "tier established" in text
    # PMID hyperlink
    assert "pubmed.ncbi.nlm.nih.gov/31157963" in text
    # Provenance hash present (sha256:<64-hex>)
    assert "sha256:" in text


async def test_wave1_runner_aborts_on_non_new_goal(tmp_path: Path) -> None:
    patient_root = tmp_path / "x"
    patient_root.mkdir()
    (patient_root / "profile.json").write_text(json.dumps({
        "patient_code": "x",
        "demographics": {},
        "diagnosis": {},
        "treatment_history": [],
        "preferences": {"depth": "technical", "language": "zh-CN"},
    }))
    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        intent_client=_Stub(['{"intent": "SMALL_TALK", "rationale": "hi"}']),
        planner_client=_Stub([]),
        executor_client=_Stub([]),
        reviewer_client=_Stub([]),
        executor_model_id="x",
        reviewer_model_id="y",
        expert_factory=lambda *a, **k: None,
        gates=[],
    )
    result = await runner.run(patient_text="hello")
    assert result["status"] == "no_team_run"
    assert result["intent"] == "SMALL_TALK"


async def test_wave1_runner_writes_provenance_journal(tmp_path: Path) -> None:
    patient_root = _setup_patient(tmp_path)
    out_dir = tmp_path / "out"
    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=out_dir,
        intent_client=_Stub(['{"intent": "NEW_GOAL", "rationale": "x"}']),
        planner_client=_Stub([
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"x"}]}'
        ]),
        executor_client=_Stub([
            '{"variants": [{"gene": "EGFR", "protein_change": "L858R", '
            '"claim_layer": "established", "evidence": [], "summary": "x"}], "summary": "x"}'
        ]),
        reviewer_client=_Stub(['{"verdict": "pass", "challenges": []}']),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )
    await runner.run(patient_text="ngs?")
    prov_path = out_dir / "provenance.jsonl"
    assert prov_path.exists()
    lines = [
        json.loads(line)
        for line in prov_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 1
    assert all("hash" in r for r in lines)
    assert all(r["hash"].startswith("sha256:") for r in lines)
