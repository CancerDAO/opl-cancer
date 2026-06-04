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
    # molecular_ngs_interpretation requires F4 (oncokb/civic/clinvar/gnomad) AND
    # F1 (pubmed). A fully-provisioned engine path wires BOTH; P0.2 now blocks
    # delivery if a wired expert is missing a required family.
    return BertExpert(
        profile=get_expert_profile("bert"),
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={
            "F1": _FakeIntegrator(),
            "F4": _FakeIntegrator(),
            "F5": _FakeIntegrator(),
        },
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


# --- P0.1: F8 family resolves for EAP integrators ---


def test_eap_deps_declare_F8_not_F3() -> None:
    """P0.1: fda_eap.py / nmpa_eap.py declare family='F8'; the trial_matching
    deps table must request F8 for the EAP context keys, not F3."""
    from opl_cancer.glue.wave1_runner import _TASK_INTEGRATOR_DEPS

    deps = dict((k, f) for k, f, _ in _TASK_INTEGRATOR_DEPS["trial_matching"])
    assert deps["fda_eap_results"] == "F8"
    assert deps["nmpa_eap_results"] == "F8"
    # And the declared family on the integrators is indeed F8.
    from opl_cancer.integrators.fda_eap import FDAEAPIntegrator
    from opl_cancer.integrators.nmpa_eap import NMPAEAPIntegrator

    assert FDAEAPIntegrator.family == "F8"
    assert NMPAEAPIntegrator.family == "F8"


# --- P0.2c: a wired-but-missing-required-family run BLOCKS, never empties ---


class _TrialFakeIntegrator:
    """Fake F3 client returning one match; used for the actionable-options test."""

    family = "F3"
    ttl_seconds = 60
    cache = None

    async def cached_fetch(self, key: str):
        return {"results": [{"nct_id": "NCT00000000"}], "key": key}


def _trial_factory_missing_f8(name, ex_id, rv_id):
    """rick wired with F3 only — F8 (EAP) deliberately NOT wired → must block."""
    from opl_cancer.experts.rick import RickExpert

    return RickExpert(
        profile=get_expert_profile("rick"),
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={"F3": _TrialFakeIntegrator()},  # NO F8
    )


_TRIAL_PLAN = {
    "experts": ["rick"],
    "tasks": [{
        "id": "t1", "expert": "rick",
        "task_package": "trial_matching", "sub_goal": "match trials",
    }],
}

_TRIAL_HOST_ARTIFACTS = {
    "trial_matching": {
        "matches": [{
            "nct_id": "NCT12345678", "title": "Phase II osimertinib in EGFR+ NSCLC",
            "phase": "II", "status": "Recruiting",
            "claim_layer": "established",
            "summary": "osimertinib trial", "evidence": [],
        }],
        "expanded_access_routes": [{
            "program": "FDA Expanded Access — osimertinib", "jurisdiction": "US",
            "claim_layer": "established", "summary": "EAP route",
        }],
        "summary": "actionable trial + EAP",
    }
}


async def test_not_wired_required_family_blocks_delivery(tmp_path: Path) -> None:
    """P0.2c: ENGINE path — a wired expert that must retrieve via Python but is
    missing a REQUIRED family (F8) blocks delivery rather than substituting
    {'results': []} the LLM fills from memory. (No host_artifacts: this is the
    single-model/engine path where retrieval IS the runner's job; when the host
    supplies the artifact, retrieval is the host's job and a missing Python
    integrator does NOT block — see test_wave1_e2e + test_render_ctx_carries_*.)"""
    patient_root = _setup_patient(tmp_path)
    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_trial_factory_missing_f8,
        gates=[],
        plan_dict=_TRIAL_PLAN,
        intent="NEW_GOAL",
    )
    result = await runner.run(patient_text="find me trials")
    assert result["status"] == "blocked", result
    fams = {e["family"] for e in result["retrieval_unavailable"]}
    assert "F8" in fams
    # The brief carries the explicit BLOCKED notice (no silent empty substitution).
    html = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(encoding="utf-8")
    assert "DELIVERY BLOCKED" in html
    assert "F8" in html


async def test_render_ctx_carries_actionable_options(tmp_path: Path) -> None:
    """P0.4: matches / studies / expanded_access_routes surface as a real
    actionable 'Paths you could take' section ABOVE the speculative block."""
    patient_root = _setup_patient(tmp_path)
    # Wire BOTH F3 and F8 so the run is NOT blocked and actionable options render.
    def _factory(name, ex_id, rv_id):
        from opl_cancer.experts.rick import RickExpert

        class _F8(_TrialFakeIntegrator):
            family = "F8"

        return RickExpert(
            profile=get_expert_profile("rick"),
            executor_model_id=ex_id,
            reviewer_model_id=rv_id,
            integrators={"F3": _TrialFakeIntegrator(), "F8": _F8()},
        )

    runner = Wave1Runner(
        patient_root=patient_root,
        out_dir=tmp_path / "out",
        executor_model_id="x", reviewer_model_id="y",
        expert_factory=_factory, gates=[],
        plan_dict=_TRIAL_PLAN, host_artifacts=_TRIAL_HOST_ARTIFACTS,
        intent="NEW_GOAL",
    )
    result = await runner.run(patient_text="find me trials")
    assert result["status"] == "ok", result
    html = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(encoding="utf-8")
    md = (tmp_path / "out" / "delivery" / "patient_brief.md").read_text(encoding="utf-8")
    # Actionable section present in both renders.
    assert "Paths you could take" in html
    assert "可以走的路" in md
    assert "NCT12345678" in html
    assert "FDA Expanded Access" in html
    # The actionable section appears ABOVE the speculative World-Unknown section.
    assert html.index("Paths you could take") < (
        html.index("World-Unknown") if "World-Unknown" in html else len(html)
    )


async def test_missing_claim_layer_defaults_speculative(tmp_path: Path) -> None:
    """P1.6: a claim with no claim_layer defaults to 'speculative' (fail toward
    humility), NOT 'exploratory', and emits a risk_card."""
    host_artifacts = {
        "molecular_ngs_interpretation": {
            "variants": [{
                "gene": "EGFR", "protein_change": "L858R",
                # NO claim_layer field on purpose.
                "evidence": [],
                "summary": "EGFR L858R variant of interest",
            }],
            "summary": "no tier declared",
        }
    }
    runner = _runner(tmp_path, host_artifacts=host_artifacts)
    await runner.run(patient_text="ngs?")
    html = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(encoding="utf-8")
    # The variant claim is tagged speculative, not exploratory.
    assert "tier speculative" in html
    assert "tier exploratory" not in html
    # A risk_card warns the tier was missing.
    assert "no/invalid claim_layer" in html or "claim_layer" in html
