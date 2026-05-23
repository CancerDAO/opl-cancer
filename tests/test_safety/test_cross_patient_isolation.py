"""Iter 19 (v1.0.11) — cross-patient isolation red-team.

Two patients with distinct memory stores. Verifies:
  1. Running Wave1Runner on patient A never bleeds patient B's data into
     the run output / provenance / brief.
  2. If an expert ever returns a foreign patient_code, the runner raises
     ``CrossPatientContaminationError`` immediately rather than silently
     proceeding.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opl_cancer.experts.bert import BertExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import (
    CrossPatientContaminationError,
    Wave1Runner,
)
from opl_cancer.llm.base import LLMRequest, LLMResponse


class _Stub:
    provider = "stub"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.responses:
            raise RuntimeError(f"_Stub out of responses for model={request.model}")
        return LLMResponse(
            content=self.responses.pop(0),
            model=request.model,
            input_tokens=1,
            output_tokens=1,
            finish_reason="end_turn",
        )


class _FakeIntegrator:
    family = "F4"
    ttl_seconds = 60
    cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        return {"verified": True, "key": key}


def _setup_patient(root: Path, code: str, diagnosis: str = "NSCLC") -> Path:
    p = root / code
    p.mkdir()
    (p / "profile.json").write_text(json.dumps({
        "patient_code": code,
        "demographics": {"age": 56, "sex": "M"},
        "diagnosis": {"primary_site": "lung", "histology": diagnosis},
        "treatment_history": [],
        "preferences": {"depth": "technical", "language": "zh-CN"},
    }))
    (p / "readiness.json").write_text("{}")
    (p / "case_text.md").write_text(f"{diagnosis} case for {code}.")
    bucket = p / "02_NGS报告"
    bucket.mkdir()
    (bucket / "ngs.txt").write_text("EGFR L858R, VAF 0.45")
    return p


def _bert_factory(name: str, exec_c: Any, rev_c: Any, ex_id: str, rv_id: str) -> Any:
    return BertExpert(
        profile=get_expert_profile("bert"),
        executor_client=exec_c,
        reviewer_client=rev_c,
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={"F4": _FakeIntegrator(), "F5": _FakeIntegrator()},
    )


def _make_runner(
    patient_root: Path, out_dir: Path, exec_payload: str,
) -> Wave1Runner:
    return Wave1Runner(
        patient_root=patient_root,
        out_dir=out_dir,
        intent_client=_Stub(['{"intent": "NEW_GOAL", "rationale": "x"}']),
        planner_client=_Stub([
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"x"}]}'
        ]),
        executor_client=_Stub([exec_payload]),
        reviewer_client=_Stub(['{"verdict": "pass", "challenges": []}']),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )


async def test_runs_on_patient_a_never_contain_patient_b(tmp_path: Path) -> None:
    """Patient A's brief never mentions patient B's code/data."""
    pa = _setup_patient(tmp_path, "patient_aaa", diagnosis="NSCLC")
    pb = _setup_patient(tmp_path, "patient_bbb", diagnosis="SCLC")  # distinct
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"

    clean_payload = (
        '{"variants": [{"gene": "EGFR", "protein_change": "L858R", '
        '"claim_layer": "established", "evidence": [], "summary": "actionable"}],'
        ' "summary": "ok"}'
    )

    res_a = await _make_runner(pa, out_a, clean_payload).run("ngs?")
    res_b = await _make_runner(pb, out_b, clean_payload).run("ngs?")
    assert res_a["status"] == "ok" and res_b["status"] == "ok"

    # Patient A's brief must not mention patient_bbb (the other case's code)
    brief_a = (out_a / "delivery" / "patient_brief.html").read_text(encoding="utf-8")
    assert "patient_bbb" not in brief_a, "patient B identifier bled into patient A brief"
    md_a = (out_a / "delivery" / "patient_brief.md").read_text(encoding="utf-8")
    assert "patient_bbb" not in md_a
    # Provenance journal must not reference patient_bbb either
    prov_a = (out_a / "provenance.jsonl").read_text(encoding="utf-8")
    assert "patient_bbb" not in prov_a

    # Symmetric check
    brief_b = (out_b / "delivery" / "patient_brief.html").read_text(encoding="utf-8")
    assert "patient_aaa" not in brief_b


async def test_mismatched_patient_code_raises(tmp_path: Path) -> None:
    """If an expert ever returns a foreign patient_code, runner raises loudly."""
    pa = _setup_patient(tmp_path, "patient_aaa")
    out_a = tmp_path / "out_a"

    # Expert output contaminated with patient_code=patient_bbb (foreign)
    poisoned_payload = (
        '{"patient_code": "patient_bbb", "variants": [{"gene": "EGFR",'
        ' "protein_change": "L858R", "claim_layer": "established",'
        ' "evidence": [], "summary": "foreign"}], "summary": "ok"}'
    )

    with pytest.raises(CrossPatientContaminationError):
        await _make_runner(pa, out_a, poisoned_payload).run("ngs?")


async def test_mismatched_patient_code_inside_claim_raises(tmp_path: Path) -> None:
    """patient_code nested inside a claim record is also detected."""
    pa = _setup_patient(tmp_path, "patient_aaa")
    out_a = tmp_path / "out_a"

    poisoned_payload = (
        '{"variants": [{"gene": "EGFR", "protein_change": "L858R",'
        ' "patient_code": "patient_bbb",'
        ' "claim_layer": "established", "evidence": [], "summary": "nested foreign"}],'
        ' "summary": "ok"}'
    )

    with pytest.raises(CrossPatientContaminationError):
        await _make_runner(pa, out_a, poisoned_payload).run("ngs?")
