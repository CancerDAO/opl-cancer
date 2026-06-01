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
