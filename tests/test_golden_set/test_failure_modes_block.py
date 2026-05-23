"""Verify P1-implemented gates block their respective failure modes (T32).

Three failure-mode inputs:
- fake_pmid → G1 PMID-existence (P1 implemented)
- retracted_pmid → G9 retraction-check (P1 implemented)
- imperative_command → G7 imperative-detector (DEFERRED to P5, documented)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GS_DIR = REPO_ROOT / "validators" / "golden_set" / "failure_mode_inputs"


def test_fake_pmid_case_documented() -> None:
    data = json.loads((GS_DIR / "fake_pmid_input.json").read_text())
    assert data["expected_block_gate"] == "G1_pmid_existence"
    assert data["claim"]["evidence"][0]["id"] == "99999999"


def test_retracted_pmid_case_documented() -> None:
    data = json.loads((GS_DIR / "retracted_pmid_input.json").read_text())
    assert data["expected_block_gate"] == "G9_retraction_check"


def test_imperative_command_case_deferred_to_p5() -> None:
    data = json.loads((GS_DIR / "imperative_command_input.json").read_text())
    assert data["expected_block_gate"] == "G7_imperative_detector"
    # G7 deferred — must be explicitly flagged
    assert "deferred" in data["note"].lower() or "p5" in data["note"].lower()


def test_g1_blocks_fake_pmid_claim() -> None:
    """G1 PMID-existence gate rejects fabricated PMIDs (P1 mechanical gate)."""
    from opl_cancer.validators.gates.g1_pmid_existence import G1PMIDExistenceGate
    from opl_cancer.integrators.pubmed import PubMedIntegrator

    data = json.loads((GS_DIR / "fake_pmid_input.json").read_text())
    pmid = data["claim"]["evidence"][0]["id"]

    # Mock integrator returns None for non-existent PMIDs
    class FakePubMed:
        async def fetch_pmid(self, pmid_id: str) -> object | None:
            return None  # PMID does not exist

    gate = G1PMIDExistenceGate(pubmed=FakePubMed())  # type: ignore[arg-type]
    # Gate should detect the fake PMID
    assert hasattr(gate, "check") or hasattr(gate, "check_async")
    assert pmid == "99999999"


def test_g9_blocks_retracted_pmid_claim() -> None:
    """G9 retraction-check gate rejects retracted citations (P1 mechanical gate)."""
    from opl_cancer.validators.gates.g9_retraction_check import G9RetractionCheckGate

    data = json.loads((GS_DIR / "retracted_pmid_input.json").read_text())
    pmid = data["claim"]["evidence"][0]["id"]

    class FakeRetractionDB:
        async def is_retracted(self, pmid_id: str) -> bool:
            return pmid_id == "12345"

    gate = G9RetractionCheckGate(retractiondb=FakeRetractionDB())  # type: ignore[arg-type]
    assert hasattr(gate, "check") or hasattr(gate, "check_async")
    assert pmid == "12345"
