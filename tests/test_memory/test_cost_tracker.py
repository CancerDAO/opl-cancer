"""v2.3 P2-#20 — cost_tracker unit tests."""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.memory.cost_tracker import (
    CostTracker,
    aggregate_cost_log,
    load_cost_log,
)


def test_record_call_writes_jsonl(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    rec = t.record_call(
        model="claude-opus-4-7",
        prompt_tokens=1000,
        completion_tokens=2000,
        latency_s=3.5,
        called_by="wave1.bert",
        wave="1",
        expert="bert",
    )
    assert rec.usd_at_time > 0
    lines = t.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["model"] == "claude-opus-4-7"
    assert parsed["prompt_tokens"] == 1000


def test_record_call_estimates_opus_pricing(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    rec = t.record_call(
        model="claude-opus-4-7",
        prompt_tokens=1_000_000,  # 1M input
        completion_tokens=1_000_000,  # 1M output
    )
    # Opus 4 default pricing: 15 + 75 = 90 per million in+out combined
    assert 89.0 < rec.usd_at_time < 91.0


def test_record_call_zero_usd_for_unknown_model(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    rec = t.record_call(
        model="my-private-model-vX",
        prompt_tokens=100, completion_tokens=200,
    )
    assert rec.usd_at_time == 0.0


def test_explicit_usd_overrides_estimate(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    rec = t.record_call(
        model="claude-opus-4-7",
        prompt_tokens=1000, completion_tokens=2000,
        usd_at_time=99.99,
    )
    assert rec.usd_at_time == 99.99


def test_record_subagent_marks_kind(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    rec = t.record_subagent(
        agent_type="opl-bert",
        prompt_tokens=500, completion_tokens=1000,
        called_by="wave1_runner.dispatch",
    )
    parsed = json.loads(t.log_path.read_text(encoding="utf-8").strip())
    assert parsed["kind"] == "subagent"
    assert parsed["agent_type"] == "opl-bert"


def test_aggregate_empty(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    agg = t.aggregate()
    assert agg["total_usd"] == 0.0
    assert agg["tokens_input"] == 0
    assert agg["by_model"] == []


def test_aggregate_groups_correctly(tmp_path: Path) -> None:
    t = CostTracker(run_dir=tmp_path)
    t.record_call(model="claude-opus-4-7", prompt_tokens=100, completion_tokens=200,
                  usd_at_time=0.05, wave="1", expert="bert")
    t.record_call(model="claude-opus-4-7", prompt_tokens=100, completion_tokens=200,
                  usd_at_time=0.05, wave="1", expert="aviv")
    t.record_call(model="gpt-5", prompt_tokens=50, completion_tokens=100,
                  usd_at_time=0.02, wave="2", expert="vince")
    agg = t.aggregate()
    assert agg["total_usd"] == 0.12
    assert agg["tokens_input"] == 250
    assert agg["tokens_output"] == 500
    # by_model
    models = {b["model"]: b for b in agg["by_model"]}
    assert "claude-opus-4-7" in models
    assert models["claude-opus-4-7"]["calls"] == 2
    assert "gpt-5" in models
    assert models["gpt-5"]["calls"] == 1
    # by_wave
    waves = {b["wave"]: b for b in agg["by_wave"]}
    assert waves["1"]["calls"] == 2
    assert waves["2"]["calls"] == 1
    # by_expert
    experts = {b["expert"]: b for b in agg["by_expert"]}
    assert experts["bert"]["calls"] == 1
    assert experts["aviv"]["calls"] == 1
    assert experts["vince"]["calls"] == 1


def test_aggregate_skips_corrupt_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "cost_log.jsonl"
    log_path.write_text(
        '{"model": "ok", "usd_at_time": 1.0}\n'
        '{not valid json\n'
        '\n'
        '{"model": "ok", "usd_at_time": 2.0}\n',
        encoding="utf-8",
    )
    agg = aggregate_cost_log(log_path)
    assert agg["total_usd"] == 3.0


def test_append_only_persists_across_instances(tmp_path: Path) -> None:
    t1 = CostTracker(run_dir=tmp_path)
    t1.record_call(model="claude-opus-4-7", prompt_tokens=100, completion_tokens=200)
    t2 = CostTracker(run_dir=tmp_path)
    t2.record_call(model="claude-opus-4-7", prompt_tokens=300, completion_tokens=400)
    records = load_cost_log(t1.log_path)
    assert len(records) == 2


def test_load_cost_log_missing_file_returns_empty(tmp_path: Path) -> None:
    records = load_cost_log(tmp_path / "does-not-exist.jsonl")
    assert records == []
