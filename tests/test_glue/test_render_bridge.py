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
