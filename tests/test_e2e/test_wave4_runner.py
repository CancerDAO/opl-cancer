"""P4.5-T4 — Wave4Runner end-to-end with host-written Aviv + Iain artifacts.

Harness-split: experts no longer call an LLM. The aviv (hypothesis_validation)
and iain (meta_analysis) reports are injected via patient_context['_host_artifacts'].
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.experts.aviv import AvivExpert
from opl_cancer.experts.iain import IainExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave4_runner import Wave4Runner


def _make_aviv() -> AvivExpert:
    return AvivExpert(
        profile=get_expert_profile("aviv"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def _make_iain() -> IainExpert:
    return IainExpert(
        profile=get_expert_profile("iain"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def _artifacts(aviv_resp: str, iain_resp: str) -> dict:
    """Host-written reports keyed by task_package (what the host agent writes)."""
    return {
        "_host_artifacts": {
            "hypothesis_validation": json.loads(aviv_resp),
            "meta_analysis": json.loads(iain_resp),
        }
    }


async def test_wave4_validated_hypothesis(tmp_path: Path) -> None:
    aviv_resp = json.dumps(
        {
            "verdict": "supported",
            "support_score": 0.8,
            "claim_layer_summary": "established",
        }
    )
    iain_resp = json.dumps({"meta_verdict": "pass", "risk_of_bias": "low"})
    aviv = _make_aviv()
    iain = _make_iain()

    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=aviv, iain=iain)
    wave2 = {
        "hypotheses": [{"id": "h1", "text": "EGFR C797S → 4th-gen TKI"}],
        "top_k": [("h1", 1500.0)],
    }
    wave3 = {
        "validations": [{"hyp_id": "h1", "validator": "aviv", "verdict": {}}],
        "analysis_runs": [{"hyp_id": "h1", "analysis_plan": {}, "bixbench_result": {}}],
    }

    payload = await runner.run("test", {"profile": {}, **_artifacts(aviv_resp, iain_resp)}, wave2, wave3)
    assert payload["n_validated"] == 1
    assert payload["n_falsified"] == 0
    assert payload["validations"][0]["survival_status"] == "validated"


async def test_wave4_falsified_hypothesis(tmp_path: Path) -> None:
    aviv_resp = json.dumps(
        {"verdict": "falsified", "support_score": -0.7, "claim_layer_summary": "exploratory"}
    )
    iain_resp = json.dumps({"meta_verdict": "pass"})
    aviv = _make_aviv()
    iain = _make_iain()

    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=aviv, iain=iain)
    wave2 = {
        "hypotheses": [{"id": "h2", "text": "unsupported claim"}],
        "top_k": [("h2", 1400.0)],
    }
    wave3 = {"validations": [], "analysis_runs": []}

    payload = await runner.run("test", _artifacts(aviv_resp, iain_resp), wave2, wave3)
    assert payload["n_falsified"] == 1
    assert payload["validations"][0]["survival_status"] == "falsified"


async def test_wave4_inconclusive_when_iain_flags(tmp_path: Path) -> None:
    aviv_resp = json.dumps(
        {"verdict": "supported", "support_score": 0.4, "claim_layer_summary": "exploratory"}
    )
    iain_resp = json.dumps({"meta_verdict": "needs_revision", "risk_of_bias": "high"})
    aviv = _make_aviv()
    iain = _make_iain()

    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=aviv, iain=iain)
    wave2 = {
        "hypotheses": [{"id": "h3", "text": "borderline claim"}],
        "top_k": [("h3", 1300.0)],
    }
    wave3 = {"validations": [], "analysis_runs": []}

    payload = await runner.run("test", _artifacts(aviv_resp, iain_resp), wave2, wave3)
    assert payload["n_inconclusive"] == 1


async def test_wave4_spawns_replan_on_contradicted_forecast(tmp_path: Path) -> None:
    """D3/ADR-0036: when Aviv judges the Wave-3 data contradicts the hypothesis's
    locked forecast and supplies a testability_path, Wave 4 spawns a replan task
    that chases the surprise (not just a failure-ledger line)."""
    aviv_resp = json.dumps({
        "verdict": "falsified", "support_score": -0.6, "claim_layer_summary": "exploratory",
        "updated_belief": {"posterior_confidence": 0.2, "surprise": "strong",
                           "what_changed": "forecast said cluster X up; data shows it down"},
        "contradicts_forecast": True,
        "surprise_testability_path": "ctDNA dual-target dynamics at 4 weeks",
    })
    iain_resp = json.dumps({"meta_verdict": "pass"})
    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=_make_aviv(), iain=_make_iain())
    wave2 = {
        "hypotheses": [{"id": "h1", "text": "EGFR C797S → 4th-gen TKI",
                        "prior_expectation": {"predicted_wave3_result": "cluster X up", "confidence_0_1": 0.7}}],
        "top_k": [("h1", 1500.0)],
    }
    wave3 = {"validations": [], "analysis_runs": []}
    payload = await runner.run("test", _artifacts(aviv_resp, iain_resp), wave2, wave3)

    assert payload["replans"], "a contradicted forecast with a testability_path must spawn a replan"
    replan = payload["replans"][0]
    assert replan["spawned"] is True and replan["hypothesis_id"] == "h1"
    assert Path(replan["replan_task_path"]).is_file()
    assert (tmp_path / "out" / "replan").is_dir()


async def test_wave4_no_replan_without_surprise(tmp_path: Path) -> None:
    """A validated hypothesis with no surprise signal spawns no replan."""
    aviv_resp = json.dumps({"verdict": "supported", "support_score": 0.8,
                            "claim_layer_summary": "established"})
    iain_resp = json.dumps({"meta_verdict": "pass"})
    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=_make_aviv(), iain=_make_iain())
    wave2 = {"hypotheses": [{"id": "h1", "text": "x",
                            "prior_expectation": {"predicted_wave3_result": "up", "confidence_0_1": 0.6}}],
             "top_k": [("h1", 1500.0)]}
    wave3 = {"validations": [], "analysis_runs": []}
    payload = await runner.run("test", _artifacts(aviv_resp, iain_resp), wave2, wave3)
    assert payload["replans"] == []
    assert not (tmp_path / "out" / "replan").exists()


async def test_wave4_writes_artifacts(tmp_path: Path) -> None:
    aviv_resp = json.dumps({"verdict": "supported", "support_score": 0.9, "claim_layer_summary": "established"})
    iain_resp = json.dumps({"meta_verdict": "pass"})
    aviv = _make_aviv()
    iain = _make_iain()

    runner = Wave4Runner(out_dir=tmp_path / "out", aviv=aviv, iain=iain)
    wave2 = {
        "hypotheses": [{"id": "hx", "text": "x"}],
        "top_k": [("hx", 1500.0)],
    }
    wave3 = {"validations": [], "analysis_runs": []}

    payload = await runner.run("test", _artifacts(aviv_resp, iain_resp), wave2, wave3)
    run_dir = tmp_path / "out" / payload["run_id"]
    assert (run_dir / "wave4_validation.json").exists()
    assert (run_dir / "provenance.jsonl").exists()
    prov_lines = (run_dir / "provenance.jsonl").read_text().strip().splitlines()
    assert len(prov_lines) >= 2  # aviv + iain stages
