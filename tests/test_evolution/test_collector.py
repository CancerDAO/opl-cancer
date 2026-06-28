"""Collector tests — build a TraceDigest from a synthetic run dir."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.evolution.collector import collect_trace_digest


def _make_synthetic_run(tmp_path: Path, with_synergy: bool = True) -> Path:
    run_dir = tmp_path / "run-synthetic"
    run_dir.mkdir()
    (run_dir / "tasks").mkdir()
    for n in (1, 2):
        (run_dir / "tasks" / f"w{n}_aviv").mkdir()
        (run_dir / "tasks" / f"w{n}_aviv" / "report.md").write_text(
            "all good\n", encoding="utf-8"
        )
    # Wave 1 with an error
    (run_dir / "tasks" / "w1_bert").mkdir()
    (run_dir / "tasks" / "w1_bert" / "report.md").write_text(
        "## note\nfailed to retrieve PMID 36546659\n", encoding="utf-8"
    )
    # Wave 2 output
    hyps = [
        {
            "id": "h1",
            "claim_layer": "established",
            "generation_strategy": "literature_gap",
        },
    ]
    if with_synergy:
        hyps.append(
            {
                "id": "h2",
                "claim_layer": "speculative",
                "generation_strategy": "target_synergy_emergent",
                "testability_path": "DepMap KRAS+SHP2 co-essentiality",
            }
        )
        hyps.append(
            {
                "id": "h3",
                "claim_layer": "speculative",
                "generation_strategy": "undrugged_target_design",
                "testability_path": "ESMFold PRMT5 + DiffDock screen",
            }
        )
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": hyps}), encoding="utf-8"
    )
    # Henry verdicts
    (run_dir / "tasks" / "henry").mkdir()
    (run_dir / "tasks" / "henry" / "h1").mkdir()
    (run_dir / "tasks" / "henry" / "h1" / "verdict.json").write_text(
        json.dumps({"verdict": "pass"}), encoding="utf-8"
    )
    (run_dir / "tasks" / "henry" / "h2").mkdir()
    (run_dir / "tasks" / "henry" / "h2" / "verdict.json").write_text(
        json.dumps({"verdict": "needs_revision"}), encoding="utf-8"
    )
    # Delivery brief
    (run_dir / "delivery").mkdir()
    brief = "<html>...World-Unknown research direction...</html>" if with_synergy else "<html>summary only</html>"
    (run_dir / "delivery" / "patient_brief.html").write_text(brief, encoding="utf-8")
    return run_dir


def test_collector_picks_up_wave_summaries(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    d = collect_trace_digest(run_dir)
    waves = {w.wave: w for w in d.waves}
    assert 1 in waves
    assert 2 in waves
    assert waves[1].tasks_completed >= 2  # w1_aviv + w1_bert
    assert any("failed" in e.lower() for e in waves[1].errors)


def test_collector_picks_up_hypothesis_strategies(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path, with_synergy=True)
    d = collect_trace_digest(run_dir)
    strats = {h.strategy for h in d.hypothesis_strategies}
    assert "target_synergy_emergent" in strats
    assert "undrugged_target_design" in strats
    syn = [h for h in d.hypothesis_strategies if h.strategy == "target_synergy_emergent"][0]
    assert syn.speculative_with_testability == 1


def test_collector_detects_weak_run(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path, with_synergy=False)
    d = collect_trace_digest(run_dir)
    strats = {h.strategy for h in d.hypothesis_strategies}
    assert "target_synergy_emergent" not in strats
    assert "undrugged_target_design" not in strats


def test_collector_henry_verdicts(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    d = collect_trace_digest(run_dir)
    assert d.henry_verdict_counts.get("pass", 0) >= 1
    assert d.henry_verdict_counts.get("needs_revision", 0) >= 1


def test_collector_novelty_gate_stats(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path, with_synergy=True)
    d = collect_trace_digest(run_dir)
    assert d.novelty_gate_stats.get("world_unknown_section_present") == 1


def test_collector_size_bounded(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    d = collect_trace_digest(run_dir)
    assert d.digest_byte_size_estimate > 0
    assert d.digest_byte_size_estimate < 100_000  # 100KB cap target


def test_collector_captures_strange_tail(tmp_path: Path):
    """D4/ADR-0037: the collector reads the REAL failure tail (reviewer fails,
    falsified verdicts, G14 low cohort-match) — not just 5 keyword-grepped lines."""
    run_dir = _make_synthetic_run(tmp_path)
    # a reviewer-fail with a reason
    (run_dir / "tasks" / "w1_bert" / "review.json").write_text(
        json.dumps({"status": "fail", "result": {"reason": "claim unsupported by cited PMID"}}),
        encoding="utf-8",
    )
    # a falsified Wave-4 verdict
    (run_dir / "wave4_validation.json").write_text(
        json.dumps({"validations": [
            {"hyp_id": "h1", "hypothesis_text": "KRAS combo", "survival_status": "falsified"}]}),
        encoding="utf-8",
    )
    # a G14 low cohort-match in the delivery attestation
    (run_dir / "delivery" / "DELIVERY_ATTESTATION.json").write_text(
        json.dumps({"gate_results": [
            {"gate": "G14_dataset_patient_match", "status": "fail", "block": False,
             "message": "weak match", "evidence": {"match_score": 0.42}}]}),
        encoding="utf-8",
    )
    d = collect_trace_digest(run_dir)
    kinds = {s["kind"] for s in d.strange_tail}
    assert "reviewer_fail" in kinds
    assert "falsified_hypothesis" in kinds
    assert "g14_low_match" in kinds
    # the reason text is carried, not just a count
    assert any("unsupported" in s["reason"] for s in d.strange_tail if s["kind"] == "reviewer_fail")


def test_collector_strange_tail_empty_on_clean_run(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    d = collect_trace_digest(run_dir)
    assert d.strange_tail == []


def test_collector_raises_on_missing_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        collect_trace_digest(tmp_path / "nonexistent")
