"""Wave-1 scaffold wiring (harness-split), verified offline.

The in-Python LLM dispatch was removed; the host agent is the executor. This
proves the wiring (generic scaffold/validate expert factory + run_wave1_scaffold)
(a) builds an expert for ANY roster persona, (b) when host-written report
artifacts are supplied, assembles the brief + provenance journal + per-expert
reports the downstream gates read, and (c) without artifacts returns an honest
"incomplete" status (scaffolds persisted, no fabricated brief). Fully offline.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.wave1_live import build_default_expert_factory, run_wave1_scaffold


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


_PLAN = {
    "experts": ["bert"],
    "tasks": [{
        "id": "t1", "expert": "bert",
        "task_package": "molecular_ngs_interpretation", "sub_goal": "interpret ngs",
    }],
}

# A host-agent-written report artifact (what a subagent running
# prompts/experts/expert_task_package.md would write back), keyed by task_package.
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


def test_default_factory_builds_any_roster_expert() -> None:
    """The generic factory builds a working expert for personas with NO concrete
    subclass (vince, empty portfolio) and the v2 additions (maya/julius) —
    harness-split signature (name, executor_model_id, reviewer_model_id)."""
    factory = build_default_expert_factory()
    vince = factory("vince", "exec-id", "rev-id")
    assert vince.profile.name == "vince"
    assert vince.can_handle("anything")  # empty portfolio → trusts planner routing
    for n in ("maya", "julius", "frances", "rosa"):
        assert factory(n, "e", "r").profile.name == n


def test_wave1_scaffold_with_host_artifacts_assembles_brief(tmp_path: Path) -> None:
    """run_wave1_scaffold with host-written artifacts drives the real Wave1Runner
    and leaves the artifacts audit/deliver/attest look for — fully offline."""
    patient = _patient(tmp_path)
    run_root = tmp_path / "triggers" / "r1"
    run_root.mkdir(parents=True)
    (run_root / "plan.json").write_text(json.dumps(_PLAN), encoding="utf-8")

    result = run_wave1_scaffold(
        patient_root=patient, run_root=run_root,
        host_artifacts=_HOST_ARTIFACTS,
    )
    assert result["status"] == "ok", result
    assert result["scaffolded_experts"] == []
    assert (run_root / "provenance.jsonl").exists(), "provenance journal must be written"
    reports = list(run_root.glob("tasks/w1_*/report.md"))
    assert reports, "at least one per-expert report must be written"
    assert any("bert" in r.read_text(encoding="utf-8") for r in reports)
    brief = run_root / "delivery" / "patient_brief.html"
    assert brief.exists()
    assert "EGFR" in brief.read_text(encoding="utf-8")


def test_wave1_scaffold_without_artifacts_is_incomplete(tmp_path: Path) -> None:
    """No host-written report → honest incomplete status + scaffold persisted,
    never a fabricated brief (memory:feedback_no_false_completion)."""
    patient = _patient(tmp_path)
    run_root = tmp_path / "triggers" / "r2"
    run_root.mkdir(parents=True)
    (run_root / "plan.json").write_text(json.dumps(_PLAN), encoding="utf-8")

    result = run_wave1_scaffold(patient_root=patient, run_root=run_root)
    assert result["status"] == "incomplete", result
    assert "bert" in result["scaffolded_experts"]
    # The per-expert scaffold report is still written (carries the prompt to run).
    reports = list(run_root.glob("tasks/w1_*/report.md"))
    assert reports
    body = reports[0].read_text(encoding="utf-8")
    assert "scaffold" in body.lower()
