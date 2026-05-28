"""Tests for v2.5 CancerContextGenerator — RFC 0001 §2.3."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from opl_cancer.cancer_context import CancerContextGenerator
from opl_cancer.cli import main


# ─── seed JSONs ────────────────────────────────────────────────────────────


def test_hcc_seed_returns_json() -> None:
    gen = CancerContextGenerator("C22.0")
    ctx = gen.generate()
    assert ctx["icdo3"] == "C22.0"
    assert "soc_chain" in ctx
    assert "frequent_actionables" in ctx
    assert "typical_comorbidities" in ctx
    assert "imaging" in ctx
    assert "active_trials_summary" in ctx
    assert "display_name" in ctx
    # HCC seed must NOT be a scaffold stub
    assert "_status" not in ctx or ctx.get("_status") != "scaffold_pending_M6"


def test_nsclc_egfr_seed_returns_json() -> None:
    gen = CancerContextGenerator("C34.9_EGFR")
    ctx = gen.generate()
    assert ctx["icdo3"] == "C34.9_EGFR"
    assert ctx["display_name"]
    assert isinstance(ctx["frequent_actionables"], list)
    assert isinstance(ctx["soc_chain"], list)
    assert "_status" not in ctx or ctx.get("_status") != "scaffold_pending_M6"


def test_novel_cancer_returns_scaffold_stub(tmp_path: Path) -> None:
    """For a cancer code with no seed, generator writes a scaffold stub explaining
    M6 deferral."""
    gen = CancerContextGenerator("C00.0_NOVEL", cache_dir=tmp_path)
    ctx = gen.generate()
    # scaffold stub MUST have status field
    assert ctx.get("_status") == "scaffold_pending_M6"
    assert ctx["icdo3"] == "C00.0_NOVEL"
    # All schema keys must still be present (empty defaults OK)
    for k in (
        "display_name",
        "soc_chain",
        "frequent_actionables",
        "typical_comorbidities",
        "imaging",
        "active_trials_summary",
    ):
        assert k in ctx


def test_force_refresh_writes_new_file(tmp_path: Path) -> None:
    """force_refresh=True writes a scaffold stub even if cache exists."""
    cache = tmp_path / "C00.0_NOVEL.json"
    cache.write_text(json.dumps({"icdo3": "C00.0_NOVEL", "stale": True}))
    gen = CancerContextGenerator("C00.0_NOVEL", cache_dir=tmp_path, force_refresh=True)
    ctx = gen.generate()
    # force_refresh re-generates the scaffold; "stale" key must be gone
    assert "stale" not in ctx
    assert ctx.get("_status") == "scaffold_pending_M6"


# ─── CLI ──────────────────────────────────────────────────────────────────


def test_cli_generate_cancer_context_hcc(tmp_path: Path) -> None:
    out_path = tmp_path / "hcc.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["generate-cancer-context", "--icdo3", "C22.0", "--output", str(out_path)],
    )
    assert result.exit_code == 0, result.output
    assert out_path.is_file()
    ctx = json.loads(out_path.read_text())
    assert ctx["icdo3"] == "C22.0"


def test_cli_generate_cancer_context_novel_returns_scaffold(tmp_path: Path) -> None:
    out_path = tmp_path / "novel.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["generate-cancer-context", "--icdo3", "C99.0_FAKE", "--output", str(out_path)],
    )
    assert result.exit_code == 0, result.output
    ctx = json.loads(out_path.read_text())
    assert ctx.get("_status") == "scaffold_pending_M6"


def test_cli_generate_cancer_context_force_refresh(tmp_path: Path) -> None:
    out_path = tmp_path / "novel.json"
    out_path.write_text(json.dumps({"old": True}))
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "generate-cancer-context",
            "--icdo3",
            "C99.0_FAKE",
            "--output",
            str(out_path),
            "--force-refresh",
        ],
    )
    assert result.exit_code == 0, result.output
    ctx = json.loads(out_path.read_text())
    assert "old" not in ctx
