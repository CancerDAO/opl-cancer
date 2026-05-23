"""Iter 14 (v1.0.6) — tools/observe.py: trigger-run observability aggregator.

Spec §10. Fake trigger dirs in tmp_path; verify metric aggregation + skip-on-missing.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.observe import build_report, render_markdown


def _write_run(
    root: Path,
    run_id: str,
    *,
    token_cost: float = 0.0,
    wall_time_seconds: float = 0.0,
    claims_produced: int = 0,
    claims_withdrawn: int = 0,
    reviewer_fail_rate: float = 0.0,
    mechanical_gate_blocks: int = 0,
    drop: tuple[str, ...] = (),
) -> None:
    d = root / run_id
    d.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "token_cost": token_cost,
        "wall_time_seconds": wall_time_seconds,
        "claims_produced": claims_produced,
        "claims_withdrawn": claims_withdrawn,
        "reviewer_fail_rate": reviewer_fail_rate,
        "mechanical_gate_blocks": mechanical_gate_blocks,
    }
    for k in drop:
        payload.pop(k, None)
    (d / "run_metadata.json").write_text(json.dumps(payload), encoding="utf-8")


def test_observe_aggregates_runs(tmp_path: Path) -> None:
    """Two healthy runs aggregate via sum + mean."""
    _write_run(
        tmp_path, "run_a", token_cost=12.5, wall_time_seconds=30.0,
        claims_produced=5, claims_withdrawn=1, reviewer_fail_rate=0.1,
        mechanical_gate_blocks=2,
    )
    _write_run(
        tmp_path, "run_b", token_cost=7.5, wall_time_seconds=10.0,
        claims_produced=3, claims_withdrawn=0, reviewer_fail_rate=0.3,
        mechanical_gate_blocks=0,
    )
    report = build_report(tmp_path)
    agg = report["aggregate"]
    assert agg["runs_count"] == 2
    assert agg["token_cost_total"] == 20.0
    assert agg["wall_time_seconds_total"] == 40.0
    assert agg["claims_produced_total"] == 8
    assert agg["claims_withdrawn_total"] == 1
    assert agg["reviewer_fail_rate_mean"] == 0.2
    assert agg["mechanical_gate_blocks_total"] == 2
    assert report["skipped"] == []


def test_observe_skips_missing_metric_keys(tmp_path: Path) -> None:
    """A run with missing keys is flagged in skipped[]."""
    _write_run(tmp_path, "run_ok", token_cost=1.0)
    _write_run(tmp_path, "run_broken", drop=("token_cost", "wall_time_seconds"))
    report = build_report(tmp_path)
    # Both rows surface, but the broken one shows up in skipped[]
    skipped_ids = {s["run_id"] for s in report["skipped"]}
    assert "run_broken" in skipped_ids
    assert "run_ok" not in skipped_ids


def test_observe_renders_markdown_table(tmp_path: Path) -> None:
    """Markdown contains header + per-run row + aggregate section."""
    _write_run(
        tmp_path, "single", token_cost=1.0, wall_time_seconds=2.0,
        claims_produced=1, claims_withdrawn=0, reviewer_fail_rate=0.0,
        mechanical_gate_blocks=0,
    )
    report = build_report(tmp_path)
    md = render_markdown(report)
    assert "## Aggregate" in md
    assert "## Per-run" in md
    assert "single" in md
    assert "token_cost_total" in md
