"""Wave 3 E2E — Aviv + Tyler over mocked Wave-2 output. P3-T12.

Harness-split: experts no longer call an LLM. Per-task host-written report
artifacts are injected via patient_context['_host_artifacts'] (keyed by
task_package). Bixbench in dry-run (no OPL_BIXBENCH_LIVE set).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.compute.runner import BixbenchRunner
from opl_cancer.experts.aviv import AvivExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.experts.tyler import TylerExpert
from opl_cancer.glue.wave3_runner import Wave3Runner


_DATASET_JSON = json.dumps(
    {
        "datasets": [
            {
                "accession": "GSE12345",
                "source": "GEO",
                "title": "scRNA HCC",
                "platform": "scRNA-seq",
                "n_samples": 24,
                "cancer_type": "HCC",
                "match_score": 6,
                "match_rationale": "matches",
                "suitable_for_hyp_ids": ["hyp_a"],
                "claim_layer": "established",
            }
        ],
        "_meta": {"source_count_checked": 1},
    }
)
_ANALYSIS_JSON = json.dumps(
    {
        "analysis_plan_id": "plan_xx",
        "dataset_accessions": ["GSE12345"],
        "steps": [{"name": "QC", "tool": "scanpy", "params": {}}],
        "batch_variables": ["sample"],
        "multiple_testing_method": "BH",
        "expected_outputs": ["umap.png"],
        "falsification_rule": "no DE in cluster of interest at q<0.1",
        "compute_estimate": {"cpu_h": 1, "ram_gb": 16, "wall_h": 1},
        "claim_layer": "exploratory",
    }
)
_VALIDATION_JSON = json.dumps(
    {
        "hyp_id": "hyp_a",
        "support_score": 0.6,
        "verdict": "supported",
        "evidence_cited": [{"type": "pathway", "ref": "WNT", "direction": "+"}],
        "claim_layer_recommended": "exploratory",
        "wet_lab_experiment": {
            "validation_layer": "cell_line_required",
            "cell_line_ids": ["ACH-000739"],
            "perturbation": "CTNNB1 knockdown",
            "expected_outcome_positive": "WNT target decrease",
            "expected_outcome_negative": "no change",
        },
        "remaining_uncertainty": "Tested in HCC only",
    }
)


def _make_aviv() -> AvivExpert:
    return AvivExpert(
        profile=get_expert_profile("aviv"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


def _make_tyler() -> TylerExpert:
    return TylerExpert(
        profile=get_expert_profile("tyler"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )


# Host-written per-task report artifacts (what the host agent writes back),
# keyed by task_package — injected into patient_context so the scaffold/validate
# expert.execute() returns the real report.
def _host_artifacts() -> dict:
    return {
        "_host_artifacts": {
            "dataset_acquisition": json.loads(_DATASET_JSON),
            "bioinformatics_data_analysis": json.loads(_ANALYSIS_JSON),
            "hypothesis_validation": json.loads(_VALIDATION_JSON),
        }
    }


def _wave2_canned() -> dict:
    return {
        "hypotheses": [
            {"id": "hyp_a", "text": "WNT activation drives ICI resistance"},
            {"id": "hyp_b", "text": "Treg infiltration predicts response"},
        ],
        "top_k": [["hyp_a", 1250.0], ["hyp_b", 1180.0]],
    }


async def test_wave3_e2e_produces_validations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    runner = Wave3Runner(
        out_dir=tmp_path / "out",
        aviv=_make_aviv(),
        tyler=_make_tyler(),
        bixbench=BixbenchRunner(),
    )
    out = await runner.run(
        patient_text="Wave-3 data evidence?",
        patient_context={"cancer": "HCC", "stage": "III", **_host_artifacts()},
        wave2_outputs=_wave2_canned(),
    )
    assert out["datasets"]["datasets"][0]["accession"] == "GSE12345"
    assert len(out["analysis_runs"]) == 2
    assert len(out["validations"]) == 2
    for v in out["validations"]:
        assert v["validator"] == "tyler"
        assert v["verdict"]["support_score"] == 0.6


async def test_wave3_writes_json_and_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    runner = Wave3Runner(
        out_dir=tmp_path / "out",
        aviv=_make_aviv(),
        tyler=_make_tyler(),
        bixbench=BixbenchRunner(),
    )
    out = await runner.run("?", _host_artifacts(), _wave2_canned())
    rd = tmp_path / "out" / out["run_id"]
    assert (rd / "wave3_data_evidence.json").exists()
    assert (rd / "provenance.jsonl").exists()
    prov_lines = (rd / "provenance.jsonl").read_text().strip().splitlines()
    # 1 dataset_acquisition + 2 analysis + 2 validations
    assert len(prov_lines) == 5


async def test_wave3_bixbench_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    runner = Wave3Runner(
        out_dir=tmp_path / "out",
        aviv=_make_aviv(),
        tyler=_make_tyler(),
        bixbench=BixbenchRunner(),
    )
    out = await runner.run("?", _host_artifacts(), _wave2_canned())
    for run in out["analysis_runs"]:
        assert run["bixbench_result"]["mode"] == "dry-run"


async def test_wave3_falls_back_to_aviv_when_no_tyler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    aviv = AvivExpert(
        profile=get_expert_profile("aviv"),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
    )
    runner = Wave3Runner(
        out_dir=tmp_path / "out",
        aviv=aviv,
        tyler=None,
        bixbench=BixbenchRunner(),
    )
    out = await runner.run("?", _host_artifacts(), _wave2_canned())
    for v in out["validations"]:
        assert v["validator"] == "aviv"
