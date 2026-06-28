"""G47 — an 'established' patient-facing claim must be read deep, not abstract-deep.

B2 / ADR-0030. For an N=1 patient the subgroup forest plot in a trial supplement
and the trial's exclusion criteria decide whether a cited trial APPLIES to them.
Today PubMed parses abstract-only and the PaperQA2 corpus is never populated, so
G2 quote-match is satisfiable by an abstract substring — an 'established' HR can
pass every gate while the patient's exact subgroup showed NO benefit or was
excluded. G47 caps any established claim that leans on PMIDs but has no full-text/
supplement/subgroup-table source. Machine-verifiable (source_section enum).
"""
from __future__ import annotations

from opl_cancer.validators.gates.g47_source_section_depth import (
    G47SourceSectionDepthGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_skip_when_not_established():
    res = G47SourceSectionDepthGate().check(
        {"claim_id": "c1", "claim_layer": "exploratory",
         "evidence": [{"type": "pmid", "id": "1", "source_section": "abstract"}]}
    )
    assert res.status == GateStatus.SKIP


def test_skip_when_established_but_guideline_only():
    res = G47SourceSectionDepthGate().check(
        {"claim_id": "c1", "claim_layer": "established",
         "evidence": [{"type": "guideline", "id": "NCCN-COLON-2026"}]}
    )
    assert res.status == GateStatus.SKIP


def test_block_when_established_pmid_evidence_is_abstract_only():
    res = G47SourceSectionDepthGate().check(
        {"claim_id": "c1", "claim_layer": "established", "options": [{}, {}],
         "evidence": [{"type": "pmid", "id": "37133585", "quote": "OS 10.8mo",
                       "source_section": "abstract"}]}
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_source_section_absent():
    res = G47SourceSectionDepthGate().check(
        {"claim_id": "c1", "claim_layer": "established",
         "evidence": [{"type": "pmid", "id": "1", "quote": "q"}]}  # no source_section
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_pass_when_a_pmid_is_read_deep():
    res = G47SourceSectionDepthGate().check(
        {"claim_id": "c1", "claim_layer": "established",
         "evidence": [
             {"type": "pmid", "id": "1", "source_section": "abstract"},
             {"type": "pmid", "id": "2", "source_section": "subgroup_table"},
         ]}
    )
    assert res.status == GateStatus.PASS
