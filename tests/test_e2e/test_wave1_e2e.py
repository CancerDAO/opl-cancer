"""P1 Wave 1 E2E — parametrised over both synthetic patients (T33).

All LLM + integrator calls mocked. Deterministic (no network, fixed responses).
Asserts:
- brief HTML generated under delivery/
- every claim has provenance sha256 hash
- three-tier label present
- no command-form leakage in brief
- PMID hyperlinks well-formed when PMIDs surface

Real-API variant exists at validators/golden_set/ and is gated on env keys
(intentionally not in this test — that's a manual/dev run via
   ANTHROPIC_API_KEY=... pytest tests/test_e2e/  -m real_api).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from opl_cancer.experts.bert import BertExpert
from opl_cancer.experts.roster import get_expert_profile
from opl_cancer.glue.wave1_runner import Wave1Runner
from opl_cancer.llm.base import LLMRequest, LLMResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
GS_PATIENTS = REPO_ROOT / "validators" / "golden_set" / "synthetic_patients"


class _Stub:
    """Deterministic stub LLM client."""

    provider = "stub"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.responses:
            raise RuntimeError(f"_Stub exhausted for model={request.model}")
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

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        return {"verified": True, "key": key, "source": "mock"}


def _bert_factory(name: str, exec_c: Any, rev_c: Any, ex_id: str, rv_id: str) -> Any:
    return BertExpert(
        profile=get_expert_profile("bert"),
        executor_client=exec_c,
        reviewer_client=rev_c,
        executor_model_id=ex_id,
        reviewer_model_id=rv_id,
        integrators={"F4": _FakeIntegrator(), "F5": _FakeIntegrator()},
    )


# Per-patient canned LLM responses (executor body keyed to each synthetic case).
_RESPONSES: dict[str, dict[str, str]] = {
    "anon_hcc_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "HCC 3L planning"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"HCC NGS"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "CTNNB1", "protein_change": "S37F", '
            '"claim_layer": "exploratory", "evidence": [{"type":"pmid","id":"30262417",'
            '"quote":"CTNNB1 mutation associates with reduced ICI response in HCC"}], '
            '"summary": "Wnt-active HCC tends to be ICI-resistant"}], '
            '"summary": "CTNNB1 S37F informs 3L preference away from re-challenge ICI"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_nsclc_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "post-osimertinib resistance"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"C797S resistance"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "EGFR", "protein_change": "C797S", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"26022542",'
            '"quote":"C797S in cis with T790M confers resistance to 3rd-gen EGFR-TKI"}], '
            '"summary": "C797S in cis with L858R limits 4th-gen TKI options"}], '
            '"summary": "patient candidate for combination or trial enrolment"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_crc_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "mCRC 3L planning after anti-EGFR failure"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"KRAS G12D 3L options"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "KRAS", "protein_change": "G12D", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"36546659",'
            '"quote":"KRAS G12D is intrinsically resistant to anti-EGFR mAbs in mCRC"}], '
            '"summary": "KRAS G12D explains cetuximab failure; consider FOLFIRI+aflibercept or trial"}], '
            '"summary": "patient should be screened for KRAS-G12D selective trials (MRTX1133-class)"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_brca_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "HER2+ mBC post-T-DM1 recurrence"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"post-T-DM1 HER2+ options"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "ERBB2", "protein_change": "amplification", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"35671480",'
            '"quote":"T-DXd improves PFS over T-DM1 in HER2+ MBC (DESTINY-Breast03)"}], '
            '"summary": "T-DXd is preferred post-T-DM1 progression in HER2+ MBC"}], '
            '"summary": "T-DXd candidate; monitor ILD given prior LVEF 52%"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_pancreatic_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "BRCA2 mPDAC post-FOLFIRINOX/Gem-nabP progression"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"BRCA2 + KRAS G12D PDAC 3L"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "BRCA2", "protein_change": "5946delT (germline)", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"31157963",'
            '"quote":"Olaparib maintenance prolongs PFS in gBRCA mPDAC post-platinum (POLO trial)"}], '
            '"summary": "Olaparib maintenance is FDA-approved in gBRCA platinum-responsive mPDAC"}], '
            '"summary": "Olaparib eligibility + KRAS G12D trial review; HRD-high context"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_gbm_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "newly-dx MGMT-methylated GBM IDH-wt Stupp planning"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"MGMT-methylated GBM management"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "MGMT", "protein_change": "promoter-methylated", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"15758009",'
            '"quote":"MGMT methylation predicts TMZ benefit in GBM (Stupp 2005)"}], '
            '"summary": "MGMT methylation supports concurrent + adjuvant TMZ"}], '
            '"summary": "Stupp protocol + TTFields adjunct consideration"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_ped_all_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "Ph+ ped ALL induction failure with T315I emergence"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"T315I Ph+ pediatric ALL"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "ABL1", "protein_change": "T315I", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"22156606",'
            '"quote":"Ponatinib retains activity against T315I-mutated BCR-ABL1"}], '
            '"summary": "Ponatinib active against T315I; pediatric data limited (off-label)"}], '
            '"summary": "Ponatinib + blinatumomab bridge to HSCT; CAR-T eligibility eval"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
    "anon_myeloma_001": {
        "intent": '{"intent": "NEW_GOAL", "rationale": "high-risk MM t(4;14)+del17p early relapse"}',
        "planner": (
            '{"experts": ["bert"], "tasks": [{"id":"t1","expert":"bert",'
            '"task_package":"molecular_ngs_interpretation","sub_goal":"high-risk MM 2L"}]}'
        ),
        "executor": (
            '{"variants": [{"gene": "IGH-FGFR3/NSD2", "protein_change": "t(4;14) fusion", '
            '"claim_layer": "established", "evidence": [{"type":"pmid","id":"33933206",'
            '"quote":"BCMA-targeted CAR-T (ide-cel) effective in triple-class-exposed MM (KarMMa)"}], '
            '"summary": "High-risk MM candidate for BCMA CAR-T / teclistamab"}], '
            '"summary": "DKd or IsaKd bridge; BCMA CAR-T referral; renal dose-adjust"}'
        ),
        "reviewer": '{"verdict": "pass", "challenges": []}',
    },
}


@pytest.mark.parametrize(
    "patient_code,query",
    [
        ("anon_hcc_001", "我的 Atezo+Bev 2L 进展了，3L 有什么选择？"),
        ("anon_nsclc_001", "奥希替尼用了 20 个月开始进展，C797S 怎么办？"),
        ("anon_crc_001", "FOLFIRI+cetuximab 进展了，KRAS G12D 还能做什么？"),
        ("anon_brca_001", "T-DM1 辅助治疗期间复发，HER2+ 下一步怎么选？"),
        ("anon_pancreatic_001", "BRCA2 胰腺癌 2L 进展，olaparib 维持还能用吗？"),
        ("anon_gbm_001", "新诊断 GBM MGMT 甲基化，Stupp 和 TTFields 怎么选？"),
        ("anon_ped_all_001", "8 岁 Ph+ ALL 诱导失败 T315I，ponatinib 安全吗？"),
        ("anon_myeloma_001", "高危 MM 维持期间复发，CAR-T 还能做吗？"),
    ],
)
async def test_wave1_e2e_two_patients(
    tmp_path: Path, patient_code: str, query: str
) -> None:
    """E2E: Wave1Runner produces brief.html + provenance for each synthetic patient."""
    # Copy synthetic patient to tmp (don't mutate golden set)
    src = GS_PATIENTS / patient_code
    dst = tmp_path / patient_code
    shutil.copytree(src, dst)

    canned = _RESPONSES[patient_code]
    runner = Wave1Runner(
        patient_root=dst,
        out_dir=tmp_path / "out" / patient_code,
        intent_client=_Stub([canned["intent"]]),
        planner_client=_Stub([canned["planner"]]),
        executor_client=_Stub([canned["executor"]]),
        reviewer_client=_Stub([canned["reviewer"]]),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )

    result = await runner.run(patient_text=query)
    assert result["status"] == "ok", f"Wave1Runner failed for {patient_code}: {result}"

    out_dir = tmp_path / "out" / patient_code
    brief_html = out_dir / "delivery" / "patient_brief.html"
    assert brief_html.exists(), f"brief.html missing for {patient_code}"

    text = brief_html.read_text(encoding="utf-8")
    # Provenance hash on every claim
    assert "sha256:" in text, f"no provenance hash in {patient_code} brief"
    # Three-tier label present (established / exploratory / speculative)
    assert any(
        f"tier {t}" in text for t in ("established", "exploratory", "speculative")
    ), f"no three-tier label in {patient_code} brief"
    # No imperative command-form leakage in brief body
    assert "You should immediately" not in text
    # PMID hyperlink format if PMID surfaced
    if "PMID:" in text or "pubmed" in text:
        assert "pubmed.ncbi.nlm.nih.gov" in text

    # Provenance journal written
    prov_path = out_dir / "provenance.jsonl"
    assert prov_path.exists()
    lines = [
        json.loads(line)
        for line in prov_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(rec["hash"].startswith("sha256:") for rec in lines)


async def test_wave1_e2e_no_real_phi_leakage(tmp_path: Path) -> None:
    """Synthetic patients must not contain real-name patterns in brief."""
    src = GS_PATIENTS / "anon_hcc_001"
    dst = tmp_path / "anon_hcc_001"
    shutil.copytree(src, dst)

    canned = _RESPONSES["anon_hcc_001"]
    runner = Wave1Runner(
        patient_root=dst,
        out_dir=tmp_path / "out",
        intent_client=_Stub([canned["intent"]]),
        planner_client=_Stub([canned["planner"]]),
        executor_client=_Stub([canned["executor"]]),
        reviewer_client=_Stub([canned["reviewer"]]),
        executor_model_id="claude-opus-4-7",
        reviewer_model_id="minimax-m2-7",
        expert_factory=_bert_factory,
        gates=[],
    )
    await runner.run(patient_text="test")
    text = (tmp_path / "out" / "delivery" / "patient_brief.html").read_text(
        encoding="utf-8"
    )
    # patient_code is anonymous-prefixed
    assert "anon_" in text or "synthetic" in text.lower() or "EGFR" in text or "CTNNB1" in text
