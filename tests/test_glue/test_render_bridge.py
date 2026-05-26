"""Bridge tests — Wave 2 → renderer World-Unknown candidates."""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.render_bridge import (
    load_world_unknown_candidates,
    passes_testability_keyword_floor,
)


def _write_wave2(run_dir: Path, hyps: list[dict]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": hyps}), encoding="utf-8"
    )
    return run_dir


def test_load_filters_speculative_with_testability(tmp_path: Path):
    run_dir = _write_wave2(tmp_path / "r1", [
        {"id": "h1", "claim_layer": "established", "generation_strategy": "feasibility_first"},
        {
            "id": "h2",
            "claim_layer": "speculative",
            "generation_strategy": "target_synergy_emergent",
            "testability_path": "DepMap co-essentiality query KRAS+SHP2; CRISPR PDX dual knockout",
        },
    ])
    out = load_world_unknown_candidates(run_dir)
    assert len(out) == 1
    assert out[0]["id"] == "h2"


def test_load_rejects_short_testability_path(tmp_path: Path):
    """testability_path of 'TBD' or 'see refs' must be filtered."""
    run_dir = _write_wave2(tmp_path / "r2", [
        {
            "id": "h1",
            "claim_layer": "speculative",
            "generation_strategy": "target_synergy_emergent",
            "testability_path": "TBD",
        },
        {
            "id": "h2",
            "claim_layer": "speculative",
            "generation_strategy": "undrugged_target_design",
            "testability_path": "",
        },
    ])
    out = load_world_unknown_candidates(run_dir)
    assert len(out) == 0


def test_load_caps_at_five(tmp_path: Path):
    hyps = [
        {
            "id": f"h{i}",
            "claim_layer": "speculative",
            "generation_strategy": "target_synergy_emergent",
            "testability_path": "DepMap co-essentiality screen of dual targets in CRC PDX",
        }
        for i in range(10)
    ]
    run_dir = _write_wave2(tmp_path / "r3", hyps)
    out = load_world_unknown_candidates(run_dir)
    assert len(out) == 5


def test_load_returns_empty_when_no_wave2_file(tmp_path: Path):
    run_dir = tmp_path / "r4"
    run_dir.mkdir()
    out = load_world_unknown_candidates(run_dir)
    assert out == []


def test_load_returns_empty_when_malformed_json(tmp_path: Path):
    run_dir = tmp_path / "r5"
    run_dir.mkdir()
    (run_dir / "wave2_hypotheses.json").write_text("not json", encoding="utf-8")
    out = load_world_unknown_candidates(run_dir)
    assert out == []


def test_passes_testability_keyword_floor_positive():
    assert passes_testability_keyword_floor("DepMap co-essentiality KRAS+SHP2 + CRISPR PDX")
    assert passes_testability_keyword_floor("BLI against recombinant target Y then phenotypic rescue")
    assert passes_testability_keyword_floor("ESMFold model + DiffDock virtual screen")


def test_passes_testability_keyword_floor_negative():
    assert not passes_testability_keyword_floor("TBD")
    assert not passes_testability_keyword_floor("see references for further reading")
    assert not passes_testability_keyword_floor("")
    assert not passes_testability_keyword_floor("future research direction")


# v2.0.2 round-2 review: drug-class redaction + actionability tier


def test_drug_specifics_redacted_from_text(tmp_path: Path):
    """Patient + family reviewers said brand-name drugs invite off-label use."""
    run_dir = _write_wave2(tmp_path / "r6", [
        {
            "id": "h1",
            "claim_layer": "speculative",
            "generation_strategy": "target_synergy_emergent",
            "text": "Combine sotorasib + RMC-4630 + everolimus to attack G12C resistance.",
            "testability_path": "PDO viability assay 6x6 dose matrix adagrasib + RMC-4630 + everolimus",
        },
    ])
    out = load_world_unknown_candidates(run_dir)
    assert len(out) == 1
    c = out[0]
    # Specific brand names gone; class names present
    assert "sotorasib" not in c["text"].lower()
    assert "RMC-4630" not in c["text"]
    assert "everolimus" not in c["text"].lower()
    assert "KRAS G12C" in c["text"]
    assert "SHP2" in c["text"]
    assert "mTORC1" in c["text"]
    # Audit trail records what was redacted
    assert "sotorasib" in c["redacted_drug_names"]
    assert "rmc-4630" in c["redacted_drug_names"]


def test_actionability_tier_classified(tmp_path: Path):
    """Patient + family reviewers wanted priority ranking."""
    run_dir = _write_wave2(tmp_path / "r7", [
        {
            "id": "a",
            "claim_layer": "speculative",
            "generation_strategy": "feasibility_first",
            "text": "test",
            "testability_path": "燃石 NGS panel + 血清 25-OHD; both standard 三甲 lab orders this week",
        },
        {
            "id": "b",
            "claim_layer": "speculative",
            "generation_strategy": "target_synergy_emergent",
            "text": "test",
            "testability_path": "DepMap CRISPR Achilles cross-essentiality computational query",
        },
        {
            "id": "c",
            "claim_layer": "speculative",
            "generation_strategy": "undrugged_target_design",
            "text": "test",
            "testability_path": "ESMFold + DiffDock virtual screen, then IND-enabling synthesis",
        },
    ])
    out = load_world_unknown_candidates(run_dir)
    tiers = [c["actionability_tier"] for c in out]
    # actionable_this_week ranked first (sort-by-tier)
    assert tiers[0] == "actionable_this_week"
    # research_only ranked last
    assert tiers[-1] in ("research_only", "months_or_more")


def test_actionability_label_chinese(tmp_path: Path):
    run_dir = _write_wave2(tmp_path / "r8", [
        {
            "id": "a",
            "claim_layer": "speculative",
            "generation_strategy": "feasibility_first",
            "text": "test",
            "testability_path": "燃石 NGS panel actionable this week 三甲 lab orders",
        },
    ])
    out = load_world_unknown_candidates(run_dir)
    assert "本周" in out[0]["actionability_label_zh"]
