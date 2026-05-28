"""Tests for v2.2 P1-#11 numeric-quote verifier chain.

After Iain emits a meta-analysis report, the reviewer_hook automatically
chains the `prompts/auditor/quote_verify_numerics.md` auditor to verify
per-PMID n_resp / n_total numerics. Mismatches block downstream waves.
"""
from __future__ import annotations

from pathlib import Path

from opl_cancer.orchestrator.reviewer_hook import (
    run_numeric_verifier_chain,
    should_run_numeric_verifier,
)


def test_should_run_numeric_verifier_triggers_on_iain_meta() -> None:
    assert should_run_numeric_verifier(
        primary_expert="iain", task_package="meta_analysis"
    )


def test_should_run_numeric_verifier_skips_on_other_expert() -> None:
    assert not should_run_numeric_verifier(
        primary_expert="bert", task_package="meta_analysis"
    )


def test_should_run_numeric_verifier_skips_on_other_task() -> None:
    assert not should_run_numeric_verifier(
        primary_expert="iain", task_package="literature_synthesis"
    )


def test_run_numeric_verifier_chain_returns_none_when_skipped(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("non-meta report", encoding="utf-8")
    out = run_numeric_verifier_chain(
        report_path=report,
        primary_expert="bert",
        primary_model="claude-opus-4-7",
        task_package="hypothesis_generation",
    )
    assert out is None
    # No auditor file should be written
    assert not (tmp_path / "numeric_verifier.json").exists()


def test_run_numeric_verifier_chain_writes_audit_file(tmp_path: Path) -> None:
    report = tmp_path / "meta_report.md"
    report.write_text("meta-analysis content", encoding="utf-8")
    out = run_numeric_verifier_chain(
        report_path=report,
        primary_expert="iain",
        primary_model="claude-opus-4-7",
        task_package="meta_analysis",
    )
    assert out is not None
    audit_json = tmp_path / "numeric_verifier.json"
    assert audit_json.exists()
    assert out.get("overall_status") in ("pass", "fail")


def test_auditor_prompt_exists() -> None:
    """The auditor prompt template is shipped with the repo."""
    p = Path(__file__).resolve().parents[2] / "prompts" / "auditor" / "quote_verify_numerics.md"
    assert p.exists(), f"missing {p}"
    body = p.read_text(encoding="utf-8")
    assert "chained_after: meta_analysis" in body
    assert "n_resp" in body
    assert "block_downstream" in body
