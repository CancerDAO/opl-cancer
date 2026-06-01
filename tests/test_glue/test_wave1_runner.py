"""Test Wave1Runner as a scaffold/validate pass (harness-split).

The in-Python LLM calls (intent / planner / executor / reviewer) are removed.
The runner now loads a deterministic plan + assembles the brief from
host-written report artifacts. These tests inject the plan + host artifacts and
verify the full pipeline produces a patient_brief.html with three-tier labels +
PMID links + provenance hash — no LLM client involved.
"""
import json
from pathlib import Path
from typing import Any

from opl_cancer.experts.bert import BertExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import Wave1Runner


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


def _bert_factory(name: str, ex_id: str, rv_id: str) -> Any:
    # Harness-split factory signature: (name, executor_model_id, reviewer_model_id).
    return BertExpert(
        profile=get_expert_profile("bert"),
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={"F4": _FakeIntegrator(), "F5": _FakeIntegrator()},
    )


_PLAN = {
    "experts": ["bert"],
    "tasks": [{
        "id": "t1", "expert": "bert",
        "task_package": "molecular_ngs_interpretation", "sub_goal": "interpret ngs",
    }],
}

# Host-agent-written report keyed by task_package.
_HOST_ARTIFACTS = {
    "molecular_ngs_interpretation": {
        "variants": [{
            "gene": "EGFR", "protein_change": "L858R",
            "claim_layer": "established",
            "evidence": [{"type": "pmid", "id": "31157963", "quote": "Osimertinib improves OS"}],
            "summary": "actionable EGFR L858R",
        }],
        "summary": "actionable",
    }
}


def _runner(tmp_path: Path, *, host_artifacts=_HOST_ARTIFACTS, intent="NEW_GOAL", plan=_PLAN) -> Wave1Runner:
    patient_root = _setup_patient(tmp_path)
    return Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
        plan_dict=plan,
        host_artifacts=host_artifacts,
        intent=intent,
    )


async def test_wave1_runner_produces_brief(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = await runner.run(patient_text="我想了解我的 NGS 结果")
    assert result["status"] == "ok"

    brief_html = tmp_path / "out" / "delivery" / "patient_brief.html"
    assert brief_html.exists()
    text = brief_html.read_text(encoding="utf-8")
    assert "EGFR" in text


async def test_wave1_runner_three_tier_label_pmid_provenance(tmp_path: Path) -> None:
    """E2E assertion: brief contains three-tier label, PMID link, and provenance hash."""
    runner = _runner(tmp_path)
    await runner.run(patient_text="ngs?")
    text = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(encoding="utf-8")

    assert "tier established" in text
    assert "pubmed.ncbi.nlm.nih.gov/31157963" in text
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
        executor_model_id="x",
        reviewer_model_id="y",
        expert_factory=lambda *a, **k: None,
        gates=[],
        plan_dict=_PLAN,
        intent="SMALL_TALK",
    )
    result = await runner.run(patient_text="hello")
    assert result["status"] == "no_team_run"
    assert result["intent"] == "SMALL_TALK"


async def test_wave1_runner_writes_provenance_journal(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner = _runner(tmp_path)
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


async def test_wave1_runner_emits_run_metadata(tmp_path: Path) -> None:
    """Wave1Runner.run emits triggers/<run_id>/run_metadata.json."""
    out_dir = tmp_path / "out"
    runner = _runner(tmp_path)
    result = await runner.run(patient_text="ngs?")
    run_id = result["run_id"]
    meta_path = out_dir / "triggers" / run_id / "run_metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for k in (
        "run_id", "token_cost", "wall_time_seconds", "claims_produced",
        "claims_withdrawn", "reviewer_fail_rate", "mechanical_gate_blocks",
    ):
        assert k in meta, f"missing key {k}"
    assert meta["run_id"] == run_id
    assert meta["claims_produced"] >= 1
    assert meta["wall_time_seconds"] >= 0.0


async def test_wave1_runner_incomplete_without_host_artifacts(tmp_path: Path) -> None:
    """No host report → honest incomplete status (memory:feedback_no_false_completion)."""
    runner = _runner(tmp_path, host_artifacts={})
    result = await runner.run(patient_text="ngs?")
    assert result["status"] == "incomplete"
    assert "bert" in result["scaffolded_experts"]
