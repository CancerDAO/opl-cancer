"""ProposalWriter tests — verify output structure + safety guarantees."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opl_cancer.evolution.invariant_gate import apply_gate
from opl_cancer.evolution.models import (
    EvolutionCandidates,
    EvolutionProposal,
)
from opl_cancer.evolution.proposal_writer import write_proposals


def _make_candidates() -> EvolutionCandidates:
    p1 = apply_gate(
        EvolutionProposal(
            proposal_id="p001",
            kind="prompt_patch",
            summary="add WikiPathways to Aviv",
            rationale="enrichment missing source",
            target_path="prompts/experts/aviv/persona.md",
            proposed_diff="--- old\n+++ new\n+ WikiPathways\n",
            iter_n=1,
        )
    )
    p2 = apply_gate(
        EvolutionProposal(
            proposal_id="p002",
            kind="prompt_patch",
            summary="soften Henry L3 acknowledgment",  # SHOULD FLAG
            rationale="speed",
            target_path="src/opl_cancer/validators/henry.py",
            proposed_diff="disable requires_acknowledgment",
            iter_n=1,
        )
    )
    p3 = apply_gate(
        EvolutionProposal(
            proposal_id="p003",
            kind="skill_addition",
            summary="aggressive resistance call",
            rationale="frequent VAF >5% pattern",
            clinical_anchor="",  # MISSING — should auto-reject
            iter_n=1,
        )
    )
    p4 = apply_gate(
        EvolutionProposal(
            proposal_id="p004",
            kind="skill_addition",
            summary="cite-CSCO skill",
            rationale="reproducible pattern",
            clinical_anchor="CSCO CRC 2025 §3.2.1",
            proposed_diff="---\nname: cite-csco\n---\nbody\n",
            iter_n=1,
        )
    )
    p5 = apply_gate(
        EvolutionProposal(
            proposal_id="p005",
            kind="tool_proposal",
            summary="propose KEGG xref tool",
            rationale="reproducible enrichment gap",
            proposed_diff="def kegg_xref(): ...",
            iter_n=1,
        )
    )
    return EvolutionCandidates(
        iter_n=1,
        proposals=[p1, p2, p3, p4, p5],
        analysis_summary="test summary",
        analyzer_model="heuristic_fallback",
        used_heuristic_fallback=True,
    )


def test_writes_iter_dir_under_out_root(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    assert (out / "iter_001").exists()
    assert (out / "iter_001" / "README.md").exists()
    assert (out / "iter_001" / "status.yaml").exists()


def test_prompt_patches_concatenated_in_diff(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    diff_text = (out / "iter_001" / "prompt_patches.diff").read_text(encoding="utf-8")
    assert "Proposal p001" in diff_text
    assert "Proposal p002" in diff_text
    assert "WikiPathways" in diff_text


def test_skill_with_anchor_written_pending(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    skill_files = list((out / "iter_001" / "skill_additions").glob("*/SKILL.md.proposed"))
    assert len(skill_files) >= 1
    # cite-csco should be present, aggressive-resistance should be in rejected/
    found_csco = any("cite-csco" in str(f).lower() or "p004" in str(f) for f in skill_files)
    assert found_csco


def test_skill_without_anchor_auto_rejected(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    rejected = list((out / "iter_001" / "rejected").glob("*.md"))
    assert any("p003" in str(f) for f in rejected)
    txt = rejected[0].read_text(encoding="utf-8") if rejected else ""
    # At least one rejected file should reference clinical_anchor or invariant_gate
    rejected_text = "\n".join(f.read_text(encoding="utf-8") for f in rejected)
    assert "clinical_anchor" in rejected_text or "invariant_gate" in rejected_text


def test_status_yaml_records_double_signoff_on_henry_patch(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    yml = yaml.safe_load((out / "iter_001" / "status.yaml").read_text(encoding="utf-8"))
    p002 = next(p for p in yml["proposals"] if p["proposal_id"] == "p002")
    assert p002["requires_double_signoff"] is True
    assert p002["invariant_impact"]["touches_henry_l3_l4"] is True


def test_tool_proposals_jsonl_emitted(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    jsonl = (out / "iter_001" / "tool_proposals.jsonl").read_text(encoding="utf-8")
    assert "p005" in jsonl
    assert "KEGG xref" in jsonl


def test_writer_refuses_baseline_paths(tmp_path: Path):
    """Cannot write into src/, prompts/, models.yaml, etc."""
    forbidden = tmp_path / "src" / "opl_cancer"
    forbidden.mkdir(parents=True)
    with pytest.raises(ValueError, match="baseline path"):
        write_proposals(_make_candidates(), forbidden)


def test_writer_never_touches_baseline_files(tmp_path: Path):
    """End-to-end: after writing to tmp/proposals/, no file outside that dir is created/modified."""
    # Create a sentinel inside the parent of tmp_path
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("original", encoding="utf-8")

    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)

    assert sentinel.read_text(encoding="utf-8") == "original"
    # Everything created is under out/
    for f in tmp_path.rglob("*"):
        if f.is_file() and f != sentinel:
            assert str(f).startswith(str(out)), f"unexpected file outside out_root: {f}"


def test_readme_explains_review_protocol(tmp_path: Path):
    out = tmp_path / "proposals"
    write_proposals(_make_candidates(), out)
    readme = (out / "iter_001" / "README.md").read_text(encoding="utf-8")
    assert "double_signoff" in readme
    assert "ADR-0020" in readme
    assert "NEVER let this tool auto-apply" in readme
