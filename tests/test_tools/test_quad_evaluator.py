"""Iter 11 — tests for quad evaluator generator + aggregator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_evaluator_verdicts import (
    DIMENSIONS,
    aggregate,
    render_html,
    run,
)
from tools.run_quad_evaluation import (
    DIMENSIONS as GEN_DIMENSIONS,
    RESULT_SCHEMA,
    build_prompt,
    generate_all,
)


def test_dimension_sets_match() -> None:
    assert set(GEN_DIMENSIONS) == set(DIMENSIONS) == {
        "architecture",
        "safety",
        "code_quality",
        "ux",
    }


def test_build_prompt_each_dimension_nonempty() -> None:
    for dim in GEN_DIMENSIONS:
        text = build_prompt(dim)
        assert "Independent Evaluator" in text
        assert "Return JSON" in text
        # No paternalistic / user-echoing language
        assert "looks good" not in text.lower()


def test_build_prompt_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        build_prompt("vibes")


def test_generate_all_writes_files(tmp_path: Path) -> None:
    paths = generate_all(tmp_path)
    assert set(paths) == set(GEN_DIMENSIONS)
    for dim, p in paths.items():
        assert p.exists()
        assert p.name == f"{dim}.md"
    schema = json.loads((tmp_path / "schema.json").read_text())
    assert schema["title"] == "QuadEvaluatorVerdict"
    assert set(schema["properties"]["dimension"]["enum"]) == set(GEN_DIMENSIONS)
    assert (tmp_path / "README.md").exists()


def test_result_schema_shape() -> None:
    props = RESULT_SCHEMA["properties"]
    assert "verdict" in props
    assert set(props["verdict"]["enum"]) == {"pass", "conditional", "fail"}
    assert props["score"]["minimum"] == 0
    assert props["score"]["maximum"] == 10


def _mk_verdict(dim: str, verdict: str, score: float) -> dict[str, object]:
    return {
        "dimension": dim,
        "verdict": verdict,
        "score": score,
        "findings": [{"severity": "info", "message": "ok"}],
        "evaluator_id": f"eval-{dim}",
    }


def test_aggregate_all_pass() -> None:
    verdicts = {dim: _mk_verdict(dim, "pass", 9.0) for dim in DIMENSIONS}
    agg = aggregate(verdicts)
    assert agg["overall_verdict"] == "pass"
    assert agg["overall_score"] == 9.0
    assert agg["missing"] == []


def test_aggregate_any_fail_dominates() -> None:
    verdicts = {dim: _mk_verdict(dim, "pass", 9.0) for dim in DIMENSIONS}
    verdicts["safety"] = _mk_verdict("safety", "fail", 3.0)
    agg = aggregate(verdicts)
    assert agg["overall_verdict"] == "fail"


def test_aggregate_conditional_when_no_fail_but_conditional_present() -> None:
    verdicts = {dim: _mk_verdict(dim, "pass", 8.0) for dim in DIMENSIONS}
    verdicts["ux"] = _mk_verdict("ux", "conditional", 6.0)
    agg = aggregate(verdicts)
    assert agg["overall_verdict"] == "conditional"


def test_aggregate_missing_counts_as_conditional() -> None:
    verdicts = {
        "architecture": _mk_verdict("architecture", "pass", 9.0),
        "safety": _mk_verdict("safety", "pass", 9.0),
    }
    agg = aggregate(verdicts)
    assert agg["overall_verdict"] == "conditional"
    assert set(agg["missing"]) == {"code_quality", "ux"}


def test_render_html_includes_overall_and_dims() -> None:
    verdicts = {dim: _mk_verdict(dim, "pass", 8.5) for dim in DIMENSIONS}
    agg = aggregate(verdicts)
    html_str = render_html(agg, verdicts)
    assert "OPL Cancer" in html_str
    for dim in DIMENSIONS:
        assert dim in html_str
    assert "pass" in html_str


def test_run_end_to_end(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    verdicts_dir = workspace / "verdicts"
    verdicts_dir.mkdir()
    for dim in DIMENSIONS:
        (verdicts_dir / f"{dim}.json").write_text(
            json.dumps(_mk_verdict(dim, "pass", 9.0)), encoding="utf-8"
        )
    report, agg = run(workspace)
    assert report.exists()
    assert agg["overall_verdict"] == "pass"
    assert "OPL Cancer" in report.read_text(encoding="utf-8")


def test_run_rejects_bad_verdict(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    verdicts_dir = workspace / "verdicts"
    verdicts_dir.mkdir()
    bad = {
        "dimension": "architecture",
        "verdict": "magnificent",  # invalid
        "score": 9.0,
        "findings": [],
        "evaluator_id": "eval-x",
    }
    (verdicts_dir / "architecture.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        run(workspace)


def test_run_missing_dir_yields_all_missing(tmp_path: Path) -> None:
    report, agg = run(tmp_path)
    assert agg["overall_verdict"] == "conditional"
    assert set(agg["missing"]) == set(DIMENSIONS)
    assert report.exists()
